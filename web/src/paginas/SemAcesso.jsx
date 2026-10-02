/**
 * A tela que o perfil não abre — H94.
 *
 * Até a Sprint 07, digitar o endereço de uma tela de outro perfil montava a
 * tela assim mesmo: os filtros, o título, um "carregando…" que nunca terminava
 * e, no meio, a recusa da API. Estava seguro — a API negava —, mas quem via não
 * tinha como saber se era defeito, queda do sistema ou falta de permissão.
 *
 * Agora a página diz o que aconteceu, com o perfil de quem está usando, e
 * oferece a volta. O menu continua ao lado, com as telas que a pessoa abre.
 */
import { useLocation } from "react-router-dom";

import { useSessao } from "../api/contextoSessao";
import EstadoVazio from "../componentes/EstadoVazio";
import { useTituloDaAba } from "../componentes/tituloDaAba";
import { ROTULO_PERFIL } from "../formato";

export default function SemAcesso() {
  const { pathname } = useLocation();
  const { usuario } = useSessao();
  const perfil = ROTULO_PERFIL[usuario?.perfil] ?? usuario?.perfil;
  useTituloDaAba("Sem acesso");

  return (
    <section className="painel" aria-label="Sem acesso">
      <EstadoVazio
        titulo="O seu perfil não abre esta tela"
        texto={`O perfil ${perfil} não tem acesso a ${pathname}. As telas que você abre estão no menu. Se precisar desta, fale com o administrador do sistema.`}
        acao={{ para: "/", rotulo: "Ir para o início" }}
      />
    </section>
  );
}
