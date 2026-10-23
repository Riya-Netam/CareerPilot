/** Heading dial for the alignment score: a half-circle gauge. The needle is only a visual aid;
 *  the number and its explanation are always shown in text next to it. */
export function ScoreDial({ score }: { score: number | null }) {
  if (score === null) return <p className="text-sm text-ink-soft">No score: the posting had no recognisable skills.</p>;
  const clamp = Math.max(0, Math.min(100, score));
  const angle = Math.PI * (1 - clamp / 100);
  const cx = 110, cy = 110, r = 90;
  const nx = cx + (r - 14) * Math.cos(angle), ny = cy - (r - 14) * Math.sin(angle);
  const arc = (from: number, to: number) => {
    const a1 = Math.PI * (1 - from / 100), a2 = Math.PI * (1 - to / 100);
    return `M ${cx + r * Math.cos(a1)} ${cy - r * Math.sin(a1)} A ${r} ${r} 0 0 1 ${cx + r * Math.cos(a2)} ${cy - r * Math.sin(a2)}`;
  };
  return (
    <figure className="w-56" aria-label={`Alignment score ${clamp} out of 100`}>
      <svg viewBox="0 0 220 125" role="img" aria-hidden="true">
        <path d={arc(0, 100)} stroke="#D5DEE5" strokeWidth="14" fill="none" strokeLinecap="round" />
        {clamp > 0 && <path d={arc(0, clamp)} stroke="#1B7A8C" strokeWidth="14" fill="none" strokeLinecap="round" />}
        <line x1={cx} y1={cy} x2={nx} y2={ny} stroke="#E39B1B" strokeWidth="3" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="6" fill="#10243A" />
      </svg>
      <figcaption className="-mt-3 text-center"><span className="text-3xl font-bold">{Math.round(clamp)}</span><span className="text-sm text-ink-faint"> / 100 alignment</span></figcaption>
    </figure>
  );
}
