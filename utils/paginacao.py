import streamlit as st


def paginar(df, key_prefix, por_pagina=10):
    """Desenha os controles de paginação (Anterior/Próxima) e devolve só o recorte
    do DataFrame correspondente à página atual. Deve ser aplicado depois de qualquer
    filtro/seleção que precise operar sobre o total (ex: 'Selecionar Todos')."""
    total = len(df)
    if total == 0:
        return df

    total_paginas = max(1, -(-total // por_pagina))
    pagina_key = f"{key_prefix}_pagina"
    if pagina_key not in st.session_state:
        st.session_state[pagina_key] = 1

    pagina_atual = min(st.session_state[pagina_key], total_paginas)
    st.session_state[pagina_key] = pagina_atual

    c1, c2, c3 = st.columns([1, 2, 1])
    if c1.button("◀ Anterior", disabled=pagina_atual <= 1, key=f"{key_prefix}_prev", use_container_width=True):
        st.session_state[pagina_key] = pagina_atual - 1
        st.rerun()
    c2.markdown(
        f"<div style='text-align:center; padding-top: 6px;'>Página {pagina_atual} de {total_paginas} — {total} registro(s)</div>",
        unsafe_allow_html=True,
    )
    if c3.button("Próxima ▶", disabled=pagina_atual >= total_paginas, key=f"{key_prefix}_next", use_container_width=True):
        st.session_state[pagina_key] = pagina_atual + 1
        st.rerun()

    inicio = (pagina_atual - 1) * por_pagina
    return df.iloc[inicio:inicio + por_pagina]
