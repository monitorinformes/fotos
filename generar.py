#!/usr/bin/env python3
"""Arma la foto del Monitor de fondos (HTML plano, sin scripts) a partir de datos.json.
Uso: python3 generar.py datos.json salida.html
Solo usa la libreria estandar."""
import json, sys, os, html
from statistics import median

AQUI = os.path.dirname(os.path.abspath(__file__))
esc = lambda s: html.escape(str(s), quote=True)


def fx(v, d=2):
    s = f"{abs(v):,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if v < 0 and float(s.replace(".", "").replace(",", ".")) != 0 else "") + s


def pct(v):
    return "—" if v is None else fx(v, 2) + " %"


def pp(v):
    return ("+" if v >= 0 else "") + fx(v, 1) + " pp"


def pat_txt(v):  # v en miles de millones
    return "$ " + fx(v, 0) + " mil M" if v >= 1 else "$ " + fx(v * 1000, 0) + " M"


def tam(v):
    return "Chico" if v < 50 else ("Grande" if v >= 500 else "Mediano")


def sg(n):
    return f'<i class="sg s{n}" aria-hidden="true"></i>'


def leer(p):
    return open(os.path.join(AQUI, "plantilla", p), encoding="utf-8").read()


def chips(f):
    if not f["alarmas"]:
        return '<td class="chipcell"><span class="muted">Sin alarmas</span></td>'
    c = "".join(
        f'<span class="chip al" title="{esc(a["tipo"] + ": " + a["texto"])}">{sg(2)}{esc(a["tipo"])}'
        + (f' <b class="mono">{esc(a["valor"])}</b>' if a.get("valor") else "")
        + "</span>"
        for f_a in [f] for a in f_a["alarmas"]
    )
    return f'<td class="chipcell"><span class="chips">{c}</span></td>'


def fila(f, mejor):
    def cel(k):
        cls = "mono best" if f.get(k) is not None and f[k] == mejor[k] else "mono"
        return f'<td class="{cls}">{pct(f.get(k))}</td>'

    sub = esc(f["gestora"] + " · " + f["subcat"])
    n = esc(f["nombre"])
    return (
        f'<tr><td><button class="rowbtn" data-act="open" data-n="{n}" aria-expanded="false"><span class="nm"><i class="chev" aria-hidden="true"></i>{n}</span><span class="sub">{sub}</span></button></td>'
        f'<td><span class="pill s0">{sg(0)}OK</span></td>'
        f'<td class="mono" title="Suma de clases vigentes ({f.get("clases", 1)})"><div class="patc"><span>{pat_txt(f["pat"])}</span><span class="pill neutral" style="font-family:var(--sans)">{tam(f["pat"])}</span></div></td>'
        + cel("d30") + cel("d90") + cel("ytd") + cel("y1")
        + f'<td class="mono">{pct(f.get("vol"))}</td>'
        + chips(f) + "</tr>"
    )


def grupo(titulo, fondos, thead):
    mejor = {k: max([x[k] for x in fondos if x.get(k) is not None] or [None]) for k in ("d30", "d90", "ytd", "y1")}
    filas = "".join(fila(f, mejor) for f in sorted(fondos, key=lambda x: -(x["d90"] if x.get("d90") is not None else -1e9)))
    return (
        f'<section class="group"><header><h2>{titulo}</h2><span class="muted">{len(fondos)} fondos · se comparan entre sí por tener el mismo plazo de rescate</span></header>'
        f'<div class="tablewrap"><table>{thead}<tbody>{filas}</tbody></table></div></section>'
    )


def barras(items, mx):
    out = ""
    for it in items:
        w = max(0, it["v"]) / mx * 100 if mx else 0
        if it.get("infl"):
            out += f'<div class="hb infl"><span class="hn">{esc(it["n"])}</span><span class="ht"><i style="width:{w:.1f}%;background:var(--warn)"></i></span><span class="hv mono">{fx(it["v"], 2)} %</span></div>'
        else:
            out += f'<div class="hb"><span class="hn">{esc(it["n"])}</span><span class="ht"><i style="width:{w:.1f}%;"></i></span><span class="hv mono">{fx(it["v"], 2)} %</span></div>'
    return out


def main(entrada, salida):
    D = json.load(open(entrada, encoding="utf-8"))
    F = D["fondos"]
    M = D["mercado"]
    inf = D["inflacion"]  # mensual, ytd, d90 (numeros), mes (texto)
    head, thead, tail = leer("head.html"), leer("thead.html"), leer("tail.html")

    sin = [f for f in F if not f["alarmas"]]
    con = [f for f in F if f["alarmas"]]
    # rendimiento en el año hasta el cierre del mes del ultimo dato de inflacion (ytdInfl); si falta, se usa ytd
    ri = lambda f: f.get("ytdInfl", f.get("ytd"))
    ganan = sorted([(f, ri(f) - inf["ytd"]) for f in F if ri(f) is not None and ri(f) > inf["ytd"]], key=lambda x: -x[1])

    # encabezado
    top = (
        '<body><div id="app" class="wrap"><header class="top"><div class="meta"><span class="eyebrow">Tesorería · Cartera de FCI</span><h1>Monitor de fondos</h1>'
        f'<span class="muted">Datos de CAFCI al {esc(D["fechaDatos"])} · </span></div>'
        '<div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end">'
        f'<span class="badge foto">Foto del {esc(D["fotoGenerada"])} · no se actualiza</span></div></header>'
        '<div class="status" role="status" aria-live="polite"></div><nav class="tabs" role="tablist" aria-label="Vistas"></nav>'
    )

    def dato(nombre, valor, fecha):
        return f'<span>{nombre} <b class="mono">{esc(valor)}</b> <span class="muted">({esc(fecha)})</span></span>' if valor else ""

    ctx = (
        dato("Caución", M.get("caucion"), M.get("caucionFecha"))
        + dato("TAMAR", M.get("tamar"), M.get("tamarFecha"))
        + dato("Dólar CCL", M.get("ccl"), M.get("cclFecha"))
        + dato("Oficial", M.get("oficial"), M.get("oficialFecha"))
        + f'<span>Inflación <b class="mono">{fx(inf["mensual"], 1)} %</b> mensual · <b class="mono">{fx(inf["ytd"], 1)} %</b> en el año <span class="muted">({esc(inf["mes"])})</span></span>'
    )
    mx = ganan[0][1] if ganan else 1
    win = "".join(
        f'<div class="hb"><span class="hn" title="{esc(f["nombre"])}">{esc(f["nombre"].split(" - Clase")[0])}</span><span class="ht"><i style="width:{d / mx * 100:.1f}%"></i></span><span class="hv mono">{pp(d)}</span></div>'
        for f, d in ganan
    )
    alertas = "".join(
        f'<li>{sg(2)}<div class="t"><strong>{esc(f["nombre"])}</strong> <div class="muted">{esc(a["texto"])}</div></div></li>'
        for f in con for a in f["alarmas"]
    ) or '<li><div class="t"><span class="muted">Hoy no hay alarmas encendidas.</span></div></li>'
    resumen = (
        '<section class="summary" aria-label="Resumen"><div class="panel"><h2>Cartera y mercado</h2><div class="tiles">'
        f'<div class="tile">{sg(0)}<b>{len(sin)}</b><span class="l">Sin alarmas</span></div>'
        f'<div class="tile">{sg(2)}<b>{len(con)}</b><span class="l">Con alarmas</span></div>'
        f'<div class="tile">{sg(2)}<b>0</b><span class="l">Revisar salida</span></div></div>'
        f'<div class="ctx">{ctx}</div>'
        f'<div class="win"><h3>Le ganaron a la inflación 2026 <span class="muted">({len(ganan)} de {len(F)})</span></h3>{win}</div></div>'
        f'<div class="panel"><h2>Para mirar hoy</h2><ul class="alerts">{alertas}</ul></div></section>'
    )

    # sugerencia: sin alarmas, patrimonio >= 20 mil M, le gana a la inflacion YTD, mayor rendimiento a 90 dias
    t1 = [f for f in F if f["liq"] == "T1"]
    t0 = [f for f in F if f["liq"] == "T0"]
    med1 = median([f["d90"] for f in t1 if f.get("d90") is not None])
    med0 = median([f["d90"] for f in t0 if f.get("d90") is not None])
    cand = [f for f in F if not f["alarmas"] and f["pat"] >= 20 and ri(f) is not None and ri(f) > inf["ytd"] and f.get("d90") is not None and not f.get("peorCuartil")]
    sug = ""
    if cand:
        s = max(cand, key=lambda x: x["d90"])
        med = med1 if s["liq"] == "T1" else med0
        lab = "T+1" if s["liq"] == "T1" else "T+0"
        sug = (
            f'<section class="sugg" aria-label="Sugerencia"><span class="stag">Sugerencia</span><div><p><b>{esc(s["nombre"])}</b>. '
            f'Rinde {fx(s["d90"], 2)} % a 90 días (mediana de los {lab} de la cartera: {fx(med, 2)} %), tiene un patrimonio de {pat_txt(s["pat"])}, sin alarmas, '
            f'le ganó a la inflación 2026 ({pp(ri(s) - inf["ytd"])}).</p></div></section>'
        )

    g0 = grupo("Liquidez inmediata (T+0)", t0, thead)
    g1 = grupo("Rescate T+1", t1, thead)

    # comparativo 90 dias
    gmax = max([f["d90"] for f in F if f.get("d90") is not None] + [inf["d90"]])

    def bloque(titulo, fs, med):
        items = [{"n": f["nombre"], "v": f["d90"]} for f in fs if f.get("d90") is not None]
        items.append({"n": f'Inflación ({inf["mes"]})', "v": inf["d90"], "infl": True})
        items.sort(key=lambda x: -x["v"])
        return f'<div class="hgrp"><h3>{titulo} <span class="muted">· mediana de la cartera {fx(med, 2)} %</span></h3>{barras(items, gmax)}</div>'

    cmp_ = (
        '<section class="panel cmp" aria-label="Comparativo de rendimiento"><div class="cmph"><h2>Rendimiento de todos los fondos a 90 días</h2></div>'
        + bloque("Liquidez inmediata (T+0)", t0, med0)
        + bloque("Rescate T+1", t1, med1)
        + '<p class="note">Rendimiento a 90 días, ordenado dentro de cada grupo de plazo de rescate. En naranja, la inflación del mismo período (hasta el mes del último dato).</p></section>'
    )
    salida_html = head + top + resumen + sug + g0 + g1 + cmp_ + tail
    open(salida, "w", encoding="utf-8").write(salida_html)
    print("OK", salida, len(salida_html), "bytes;", len(F), "fondos;", len(con), "con alarmas")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("uso: python3 generar.py datos.json salida.html")
    main(sys.argv[1], sys.argv[2])
