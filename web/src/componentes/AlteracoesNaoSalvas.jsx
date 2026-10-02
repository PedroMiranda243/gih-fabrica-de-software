/**
 * O aviso de alterações não salvas — H97.
 *
 * Quem mudava um campo e clicava no menu perdia o que tinha digitado, sem
 * nenhuma palavra do sistema. Agora, com o formulário alterado (`quando`), o
 * clique num link que leva a outra tela para aqui, e a pessoa escolhe: sair sem
 * salvar ou continuar editando. Fechar a aba, recarregar ou ir a outro site
 * passa pelo aviso do próprio navegador (`beforeunload`).
 *
 * **O que fica de fora, e por quê.** O bloqueio de navegação do React Router
 * (`useBlocker`) só existe no roteador de dados, e a aplicação usa o
 * `<BrowserRouter>` com `<Routes>`: trocar o roteador por causa deste aviso
 * mexeria em todas as rotas. Por isso quem é interceptado é o **clique no
 * link** — o menu, a trilha, o "Voltar" —, que é por onde se sai de um
 * formulário. O botão voltar do navegador e "Encerrar sessão" não avisam.
 *
 * A confirmação aparece na própria página, como as outras (`Confirmacao`), e
 * recebe o foco: quem clicou no menu está olhando para o menu, e um aviso fora
 * da vista é o mesmo que nenhum.
 */
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import Confirmacao from "./Confirmacao";

/** O clique que o navegador trataria como "abrir em outro lugar" não tira ninguém da tela. */
function abreEmOutroLugar(evento, link) {
  return (
    evento.button !== 0 ||
    evento.metaKey ||
    evento.ctrlKey ||
    evento.shiftKey ||
    evento.altKey ||
    link.target === "_blank" ||
    link.hasAttribute("download")
  );
}

export default function AlteracoesNaoSalvas({ quando, className }) {
  const { pathname } = useLocation();
  const navegar = useNavigate();
  const [saindo, setSaindo] = useState(false);
  const destino = useRef(null);
  const liberado = useRef(false);
  const refAviso = useRef(null);

  useEffect(() => {
    if (!quando) return undefined;

    function aoSairDaPagina(evento) {
      evento.preventDefault();
      // Os navegadores antigos só mostram o aviso com isto.
      evento.returnValue = "";
    }

    function aoClicar(evento) {
      if (liberado.current || evento.defaultPrevented) return;
      const link = evento.target.closest?.("a[href]");
      if (!link || abreEmOutroLugar(evento, link)) return;
      // A âncora da própria página (o resumo dos erros leva ao campo) não sai dela.
      if (link.getAttribute("href").startsWith("#")) return;
      const url = new URL(link.href, window.location.href);
      // Outro site é saída da página inteira: quem avisa é o navegador.
      if (url.origin !== window.location.origin) return;
      // O mesmo endereço com outro filtro é a mesma tela, e o formulário continua nela.
      if (url.pathname === pathname) return;

      evento.preventDefault();
      destino.current = { link, caminho: url.pathname + url.search + url.hash };
      setSaindo(true);
    }

    window.addEventListener("beforeunload", aoSairDaPagina);
    /* Na captura, e no documento: roda antes do clique chegar ao `Link`, que
       não navega quando o evento já veio cancelado. */
    document.addEventListener("click", aoClicar, true);
    return () => {
      window.removeEventListener("beforeunload", aoSairDaPagina);
      document.removeEventListener("click", aoClicar, true);
      // Salvou ou trocou de tela: a pergunta que estava na tela deixou de valer.
      setSaindo(false);
    };
  }, [quando, pathname]);

  useEffect(() => {
    if (!saindo) return;
    refAviso.current?.scrollIntoView?.({ block: "center" });
    refAviso.current?.focus();
  }, [saindo]);

  if (!saindo || !quando) return null;

  function sair() {
    const { link, caminho } = destino.current;
    /* Repetir o clique, em vez de navegar por conta própria, leva junto o que o
       link carregava — o filtro da lista de onde a pessoa veio, por exemplo. */
    liberado.current = true;
    if (link.isConnected) link.click();
    else navegar(caminho);
    liberado.current = false;
    setSaindo(false);
  }

  return (
    <div className={className} role="alert" tabIndex={-1} ref={refAviso}>
      <Confirmacao
        texto="Há alterações que não foram salvas. Sair desta tela agora descarta o que você mudou."
        acao="Sair sem salvar"
        cancelar="Continuar editando"
        aoConfirmar={sair}
        aoCancelar={() => setSaindo(false)}
      />
    </div>
  );
}
