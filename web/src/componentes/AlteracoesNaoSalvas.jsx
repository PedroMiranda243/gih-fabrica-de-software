/**
 * Alterações não salvas. Com o formulário alterado (`quando`), o clique num link
 * que leva a outra tela para numa pergunta na própria página; fechar a aba ou
 * recarregar passa pelo aviso do navegador. Sem nada alterado, nada pergunta.
 *
 * O `<BrowserRouter>` não tem bloqueio de navegação; por isso quem é interceptado
 * é o clique no link (menu, trilha, "Voltar"), na captura, antes do `Link`.
 */
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import Confirmacao from "./Confirmacao";

function abreEmOutroLugar(evento, link) {
  return evento.button !== 0 || evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.altKey || link.target === "_blank" || link.hasAttribute("download");
}

export default function AlteracoesNaoSalvas({ quando }) {
  const { pathname } = useLocation();
  const navegar = useNavigate();
  const [saindo, setSaindo] = useState(false);
  const destino = useRef(null);
  const liberado = useRef(false);

  useEffect(() => {
    if (!quando) return undefined;
    function aoSair(evento) {
      evento.preventDefault();
      evento.returnValue = "";
    }
    function aoClicar(evento) {
      if (liberado.current || evento.defaultPrevented) return;
      const link = evento.target.closest?.("a[href]");
      if (!link || abreEmOutroLugar(evento, link)) return;
      if (link.getAttribute("href").startsWith("#")) return;
      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (url.pathname === pathname) return;
      evento.preventDefault();
      evento.stopPropagation();
      destino.current = { link, caminho: url.pathname + url.search + url.hash };
      setSaindo(true);
    }
    window.addEventListener("beforeunload", aoSair);
    document.addEventListener("click", aoClicar, true);
    return () => {
      window.removeEventListener("beforeunload", aoSair);
      document.removeEventListener("click", aoClicar, true);
      setSaindo(false);
    };
  }, [quando, pathname]);

  if (!saindo || !quando) return null;

  function sair() {
    const { link, caminho } = destino.current;
    liberado.current = true;
    if (link.isConnected) link.click();
    else navegar(caminho);
    liberado.current = false;
    setSaindo(false);
  }

  return (
    <div className="nao-salvas">
      <Confirmacao
        texto="Há alterações que não foram salvas. Sair desta tela agora descarta o que você mudou."
        acao="Sair sem salvar"
        cancelar="Continuar editando"
        perigo
        aoConfirmar={sair}
        aoCancelar={() => setSaindo(false)}
      />
    </div>
  );
}
