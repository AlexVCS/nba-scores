import { BaseEdge } from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';

function BracketEdge({ sourceX, sourceY, targetX, targetY, style, markerEnd, interactionWidth }: EdgeProps) {
  const midX = (sourceX + targetX) / 2;
  const edgePath = `M ${sourceX},${sourceY} H ${midX} V ${targetY} H ${targetX}`;
  return <BaseEdge path={edgePath} style={style} markerEnd={markerEnd} interactionWidth={interactionWidth} />;
}

export default BracketEdge;
