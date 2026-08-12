import io
from PIL import Image


def url_valida(valor):
    """True apenas se valor for uma string não vazia (evita NaN/None sendo tratado como imagem)."""
    return isinstance(valor, str) and bool(valor.strip())


def lista_urls(valor):
    """Divide uma string 'url1,url2' em lista, tolerando None/NaN vindos do banco/pandas."""
    if not isinstance(valor, str):
        return []
    return [u.strip() for u in valor.split(',') if u.strip()]


def converter_para_jpg_bytes(arquivo_enviado, qualidade=90):
    """Converte qualquer imagem enviada (webp, png, bmp, gif, etc.) para bytes JPEG."""
    img = Image.open(io.BytesIO(arquivo_enviado.getvalue()))
    if img.mode in ("RGBA", "P", "LA") or img.mode != "RGB":
        img = img.convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=qualidade)
    return buffer.getvalue()
