"""Recheck the saved 2026-09-10 asset comparison against live play-by-play and media.
Run from the repository root with .venv/bin/python. Does not verify browser playback.
"""
import json,re,sys,time,requests
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nba_api.stats.endpoints.playbyplayv3 import PlayByPlayV3
from server.services.nba_stats_client import NBA_STATS_HEADERS
root=Path('docs/verification/video-2026-09-10')
data=json.loads((root/'asset-comparison/retrieval.json').read_text())
report=[]
for sample in data['samples']:
 gid=sample['gameId']; pbp=PlayByPlayV3(game_id=gid,headers=NBA_STATS_HEADERS,timeout=12).get_dict()
 (root/f'pbp-{gid}.json').write_text(json.dumps(pbp,indent=2)+'\n')
 actions=pbp['game']['actions']
 for result in sample['playlists']:
  params=result['parameters'];stat=params['ContextMeasure'];rs=result.get('body',{}).get('resultSets',{});events=rs.get('playlist',[]);media=rs.get('Meta',{}).get('videoUrls',[])
  row={'gameId':gid,'seasonType':params['SeasonType'],'stat':stat,'player':result['playerName'],'playerId':params['PlayerID'],'boxscoreValue':result['boxscoreValue'],'httpStatus':result.get('httpStatus'),'eventCount':len(events),'mediaRecordCount':len(media),'validHttpsMp4Count':0,'eventChecks':[]}
  for event in events:
   matches=[a for a in actions if a['actionNumber']==event['ei'] and a['description']==event['dsc']]
   # AST rows name the shooter as personId, so verify the selected assister's
   # name in the assist credit and team using independently retrieved PBP.
   family=result['playerName'].split(' ',1)[1]
   norm=lambda s: __import__('unicodedata').normalize('NFKD',s).encode('ascii','ignore').decode().lower()
   if stat=='AST':
    identity=any(a['teamId']==params['TeamID'] and re.search(r'\('+re.escape(norm(family))+r' \d+ ast\)',norm(a['description'])) for a in matches)
    semantics=all(a['isFieldGoal']==1 and a['shotResult']=='Made' for a in matches)
   else:
    identity=any(a['personId']==params['PlayerID'] and a['teamId']==params['TeamID'] for a in matches)
    if stat in ['FGM','FGA','FG3M','FG3A','PTS']:
     semantics=all(a['isFieldGoal']==1 and (stat not in ['FGM','FG3M','PTS'] or a['shotResult']=='Made') and (stat not in ['FG3M','FG3A'] or a['shotValue']==3) for a in matches)
    elif stat in ['REB','OREB','DREB']: semantics=all(a['actionType']=='Rebound' for a in matches)
    elif stat=='STL': semantics=all(' STEAL ' in a['description'] for a in matches)
    elif stat=='BLK': semantics=all(' BLOCK ' in a['description'] for a in matches)
    elif stat=='TOV': semantics=all(a['actionType']=='Turnover' for a in matches)
    else: semantics=False
   urls=[v.get('murl') for v in media if v.get('murl') and f'/{gid}/{event["ei"]}/' in v['murl']]
   valid=[u for u in urls if urlparse(u).scheme=='https' and urlparse(u).hostname=='videos.nba.com' and urlparse(u).path.endswith('.mp4')]
   row['validHttpsMp4Count']+=bool(valid)
   row['eventChecks'].append({'eventId':event['ei'],'gameMatches':event['gi']==gid,'pbpDescriptionMatches':bool(matches),'playerAndTeamMatch':identity,'statSemanticsMatch':bool(matches) and semantics,'mediaUrlMatchesGameAndEvent':bool(valid)})
  row['metadataIdentityPass']=bool(events) and all(all(c[k] for k in ['gameMatches','pbpDescriptionMatches','playerAndTeamMatch','statSemanticsMatch']) for c in row['eventChecks'])
  # A byte-range fetch is transport evidence only, never a browser playback pass.
  first=next((v.get('murl') for v in media if v.get('murl')),None)
  if first:
   try:
    r=requests.get(first,headers={'Range':'bytes=0-1023','Referer':'https://nbascorez.com/'},timeout=12,stream=True)
    row['mediaRangeProbe']={'url':first,'at':datetime.now(timezone.utc).isoformat(),'status':r.status_code,'headers':{k:v for k,v in r.headers.items() if k.lower() in ['content-type','content-length','content-range','accept-ranges']},'first32BytesHex':next(r.iter_content(32)).hex()};r.close()
   except Exception as e: row['mediaRangeProbe']={'error':str(e)}
  report.append(row)
  print(gid,params['SeasonType'],stat,len(events),row['validHttpsMp4Count'],row['metadataIdentityPass'],flush=True)
 (root/'asset-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 time.sleep(.3)
