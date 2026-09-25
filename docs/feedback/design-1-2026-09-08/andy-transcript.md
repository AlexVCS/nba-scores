# Andy: Loom transcript

Source: https://www.loom.com/share/1dededea2de34d758d81fe2e66770304

Retrieved 2026-09-08. Loom-generated transcript, preserved without correcting recognition errors. Visual evidence and interpretation are separate.

[00:00](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=0) Hey Alex, I know you reached out to me a while ago and asked me to roast your NBA scores web app, and I took way too long to get back to you.

[00:09](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=9) I wanted to apologize for that, but you sent me kind of the new version, and I want to roast that, but I also want to kind of talk about some of the things in this earlier round and maybe maybe, you know, compare and contrast them, I opened every single link that you sent, and I realized that Design

[00:27](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=27) 4, which was this link, looked like you had merged it into NBA scores, and then there was also, there was a, I guess a third link.

[00:37](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=37) So you sent NBA scores, you sent the Design 4, and then there was a third link, here's a box score from Design 2, and it looks like that, you know, that's this one, that, that looks like that was merged into NBAscores.com as well, and then you sent me the most recent, round, which is this one, Design

[00:58](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=58) 1. So, kinda wanna dig into all of it, I guess for all intents and purposes, I can get rid of these, because it's really just these two that we're looking at, I have the mobile version, kinda opened here, and I wanna look at mobile, but I also wanna look at desktop, right out the gate, in terms of, like

[01:19](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=79) , scalability, and, just, like, balance of things, this feels better, but it also feels, like, very bland, right, and so, this one, pulling in some color with the background, and the, the, basketball, you know, floor, as the, the ground feels good, but then, on and skip.

[01:39](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=99) Some of these things just, like, feel a little too big, and when things feel too big, they often feel, you know, childish, or juvenile, or, you know, not that there's anything wrong with that, but something that more suitable to younger ages, rather than, you know, maybe an older, more mature, kind of

[01:59](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=119) , age and, and demographic. So, this feels good. Scalability, this feels good, more from, like, a brand aesthetic standpoint. Alright, I want to get into some of the, like, core functionality, so, and, and I want to do this on mobile.

[02:20](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=140) So I guess there is no iPhone 17, 16 Pro Max should be fine. I'm going to do that on both of these.

[02:26](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=146) That's back and forth between these. I don't, I'm not sure if you're using a specific library for these, but even, like, in terms of this, like, affordance for, like, switching between light mode and dark mode, that icon structure stroke feels, like, a bit thick.

[02:41](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=161) Let me see if I can find something. So, I really like ShadCN, and I'm on here. They have this toggle here.

[02:49](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=169) I don't think there's anything wrong with the icon that you're using. I think that feel, like, that makes sense and is pretty natural and maybe the icon stroke is the same in all of these.

[03:04](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=184) I, I, I'm having a hard time telling. I, I know I could inspect that, but maybe it's more, it's less a stroke width thing and more of a size thing.

[03:14](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=194) Let's see this. So, this button, which there's some tap target area, kind of like expanded outside of the icon itself to a 32-pixel button.

[03:24](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=204) but the icon, let's see if I can figure this out, is 18 by 18, the, like, actual path is more closer, is, is closer to, like, 13 1⁄2, 14-ish, so if this is 15, that's 20.

[03:45](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=225) Yeah, you know, not, not terribly different, but I think enough to, for it to kind of, like, stand out I know we already talked about the size and legibility here, scores, playoffs.

[04:02](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=242) So, I think on my phone, when I was looking at this, these buttons were actually out of view, and a lot of this stuff was just kind of, like, pushed down, you know, if you could imagine, maybe my phone is, you know, more like that, and so, I don't know how important those buttons are, but with them being

[04:23](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=263) out of view within the fold, you know, discoverability might be, might be lower than, you know, you want. Also, I know it's not NBA season, so maybe you don't have people coming to this site very often, but without their away.

[04:39](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=279) To quickly jump to when the season starts, this is, this can be a, you know, a little frustrating, and obviously I can skip forward, but then I'm like, I don't know when the season actually starts, also, I think I accidentally discovered, okay, yeah, this, clicking this opens this, but I think you need

[05:03](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=303) some sort of calendar icon affordance somewhere, for that to be, you know, more explicitly clear that this will open some sort of drawer that will allow you to kind of navigate to a specific date and time.

[05:17](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=317) Type any date back to 1946, Enter to go. That's interesting. That's cool. Yeah. I see like this calendar icon, clicking that does nothing, but I would expect something like that to be out here.

[05:29](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=329) so that I can, you know, no, that I can get to this sheet. also I don't know if like everything from above this divider is necessary.

[05:38](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=338) Like you're in here, like you, this is just kind of like duplicated redundant information, September 19th, 2026, 2026. I know we're in September, 2026 and 19th.

[05:49](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=349) So that could be redundant. also kind of, okay. So you can't go back in time, like, or maybe these lines mean.

[06:01](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=361) There are no games on that day moving forward. There's no games on these days either. So if I go into the future and I come to October 3rd, maybe there'll be games.

[06:14](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=374) Okay, cool. usually those like lines, I don't know if that's like necessarily super clear. I use this app. It's called Fotmob, which is what was the inspiration for my app.

[06:27](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=387) but Fotmob is exclusively for international football, soccer. where my app is, was originally for college football, but the whole goal was to kind of bring that Fotmob experience to American sports.

[06:39](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=399) and so I would love to even bring, NBA into the fold at some point in the future, and MLB, and, NHL, and, you know, that sort of thing.

[06:50](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=410) But, I'm opening Fotmob calendar sheet on my phone right now, and there are no lines, even on days where there aren't games which, like, Internet of National Football, there are a lot more games throughout the year, throughout the, throughout the season.

[07:11](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=431) on any given day, you could expect to see, a game at some point throughout the day. I don't know if these lines are, are necessary or doing anything, although I was able to figure out that that was when the first game was, so.

[07:26](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=446) maybe everything I said was pointless. I could also imagine, like, maybe instead of a dash on the days where there are games, maybe it's a, like, a yellow dot underneath, the number.

[07:39](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=459) I feel like I've seen that two places, but I'm not sure where. coming back here, so this is a game in the future.

[07:46](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=466) this is a card I would expect to be able to click the card, but I can't do anything. if I go back in time, also having to, like, re-anchor myself, I know it's probably because, let's see, 1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 1, 2, 3, 4.

[08:02](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=482) You know, if this was a house, a fixed size, then these buttons wouldn't constantly be shifting and changing. and so I don't have to, like, move my, you know, thumb or my mouse in this case.

[08:15](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=495) but I'm going to come to a day, like, December 18th. All right. So this is a game in the past.

[08:24](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=504) And this whole thing is like NBA scores. Right. But I can't click this. I can't see the score. And I'm just realizing that there is a button here that says reveal score.

[08:35](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=515) I don't know the, like, benefit for why we should hide the scores in games in the past. but now I can see that I can reveal the score if I want.

[08:44](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=524) we can watch. We can't see the box score. Ooh, I hadn't even gotten here. This is cool. Yeah. I, I don't know if games in the past, it's, you know, necessary to like hide the scores of the game.

[09:07](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=547) And the more I like see and I like I can understand and appreciate the detail of like the basketball background.

[09:14](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=554) It feels very reminiscent of like early iPhone days where like, I think it was like, was it the games app or maybe like, yeah, the games app had this like almost like a pool table, like that green background, or like the books had this like feeling that you were like pulling a book off of a shelf or

[09:39](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=579) the notes app, that like you're writing on a notepad. And we've kind of drifted away from that, that feel and, you know, maybe that's maybe this doesn't feel like as modern, and so I think that's why, like, I'm, I lean more towards this like simple, flat, UI direction, just something to kind of think

[10:00](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=600) about and consider. Coming into the playoffs table, this feels fine, feels good. These, like, cards with the shadows inside of a card, they're tense, there's, like, too much layers and depth, and an easy way to, like, solve that is, like, don't have shadows on literally every single thing, but sometimes

[10:21](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=621) just, like, using color to represent depth, so, like, things that are closer to, the surface, like these cards, they're closer to the light source, like a sun, and so these would be lighter and things that are, like, more recessed, can often be just, like, a darker color or a, you know, a shadowed version

[10:45](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=645) of, what's closer to you, and so this, like, background card here could be, like, a light gray, and then the, the, you know, version in the back could be even a, darker gray, you know, and flipping that into dark mode, same thing, like, these are closer to the surface, though you, your light source isn't

[11:04](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=664) a sun, but it might be the reflection of the sun off of the moon, and so these are would be lighter than the first round, card, and then the background would be even darker.

[11:16](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=676) I think that's probably enough, I could dig into this a lot more, but I think that'll probably give you enough, and this is already a 13 minute video.

[11:26](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=686) also want to point you towards, I know Claude has some, like, design critique skills, I don't know if you've used any of these, but there's also this guy named Josh Puckett who's got some, design critique skills from this InterfaceCraft, InterfaceCraft skills, so here's the curl command, that you could

[12:00](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=720) use to install it. And then, you could run the InterfaceCraft skill and ask it to, review a specific page, a specific component, for design quality, looking at hierarchy, spacing, color usage, interaction patterns, what would you improve, it's really cool, how it breaks that down, let's see if I can

[12:21](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=741) find, Design Critique skill, here's kinda like the markdown format of how it, you know, calls things out, like muddy shadows, you know, giving you an overview of the interface design and then some opportunities and you can just respond with, like, implement all three top opportunities, so that might

[12:40](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=760) be something worth considering. Granted, like, it, it can often, like, hallucinate and sometimes it's not doing a good enough job at, like, doing a critique on it in the same way that I would as a human, but it definitely is a good resource to reach for if you don't have a human to, critique your designs

[13:04](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=784) . There's also, Jakub Kryhel, he's got some skills, there's an mpx package you can install for some various different components.

[13:17](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=797) Interface review, better interface, explain interface, Here's, a breakdown of all of the skills that he has, and what they all mean and represent.

[13:28](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=808) Then there's Emil Kowalski. He's a designer at Linear. I'm currently taking his animations.dev, course, which is really cool and interesting.

[13:40](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=820) He has, Some skills. Not sure where his skills are. Emil Kowalski skills. Available skills, anime animations.

[14:04](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=844) His might be just more geared towards, animations, which maybe you could still find value in. There, you probably have heard about this, skills.sh, I think someone at the cursor meetup that we went to talked about this, but this is from Furcell.

[14:26](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=866) And then, last thing I just wanted to call out, it's not released yet, I think I may have mentioned I am expanding StatSide to also include NFL.

[14:40](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=880) It was just college football when I first launched, but I'm wanting to expand it to other sports and, in my initial version, it was more like week-based because that's the, you know, framework that college football kind of works in.

[14:54](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=894) But, FOTMOB is more day-based, so instead of week 1, 2, 3, it's just like whatever is happening to day. And so I introduced that in the newest version that has been published and it's yet to be released, but it should be coming out.

[15:08](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=908) and like I said, I eventually want to add, basketball, NHL, MLB, and I think those are the, like, next big three leagues that I want to add to this, so that you could just, like, at a glance, high level, be able to see and tell what games that you follow or even sports that you follow, are happening

[15:29](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=929) today, because, I'm sure like you and maybe a lot of other people that we know the ESPN experience can feel very clunky, pulling all this data using the ESPN API, but it is in a way more easily legible and identifiable, scannable, UI as opposed to the, like, clunky experience that ESPN offers.

[15:51](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=951) So, great work on your MBA Scores app. looking forward to seeing how it evolves and you interpret some of this feedback that I gave.

[16:01](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=961) And, try StatSide out. if you have any ideas, I'm open to hearing them. and Thanks for, you know, watching this 20 minute video and, hope to see you a meetup in the near future.

[16:14](https://www.loom.com/share/1dededea2de34d758d81fe2e66770304?t=974) Good luck. See ya.
