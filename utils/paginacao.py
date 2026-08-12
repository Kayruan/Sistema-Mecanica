import streamlit as st


def paginar(df, key_prefix, por_pagina=10):
    """Desenha o widget de paginação e devolve só o recorte do DataFrame
    correspondente à página atual. Deve ser aplicado depois de qualquer
    filtro/seleção que precise operar sobre o total (ex: "Selecionar Todos")."""
    total = len(df)
    if total == 0:
        return df

    total_paginas = max(1, -(-total // por_pagina))

    with st.container(horizontal_alignment="center"):
        st.caption(f"{total} registro(s)")
        pagina_atual = st.pagination(total_paginas, key=f"{key_prefix}_pagina")

    inicio = (pagina_atual - 1) * por_pagina
    return df.iloc[inicio:inicio + por_pagina]
