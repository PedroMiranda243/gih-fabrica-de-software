import { useEffect, useRef, useState } from "react";

/** A largura do contêiner, para desenhar o SVG em pixels de verdade (texto sem esticar). */
export function useLargura(inicial = 640) {
  const ref = useRef(null);
  const [largura, setLargura] = useState(inicial);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return undefined;
    const obs = new ResizeObserver(([entrada]) => {
      const w = Math.round(entrada.contentRect.width);
      if (w > 0) setLargura(w);
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return [ref, largura];
}
