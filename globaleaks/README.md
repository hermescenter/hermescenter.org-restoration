# Archivio storico Hermes Center per globaleaks.org

67 articoli dell'archivio storico di **hermescenter.org** (2008–2024) che riguardano GlobaLeaks,
il whistleblowing, l'anticorruzione, Transparency International e l'ANAC, già convertiti nel
formato del sito globaleaks.org, **allegati inclusi**.

Vengono dall'archivio del vecchio sito Hermes, ricostruito e ripubblicato nell'ottobre 2026
(repository [hermescenter.org-restoration](https://github.com/hermescenter/hermescenter.org-restoration)).

## Formato

globaleaks.org è un sito **Hugo** multilingua: inglese alla radice, italiano sotto `/it/`,
sezione `blog` con permalink `/anno/mese/giorno/slug/` e tassonomia `category`
(archivio su `/category/news/`). Il pacchetto rispetta queste convenzioni.

Ogni articolo è un **page bundle**: una cartella con `index.md` e, accanto, i suoi allegati.
I link nel testo sono relativi, quindi i documenti viaggiano con l'articolo.

```
content/
  blog/<slug>/index.md        24 articoli in inglese
  it/blog/<slug>/index.md     43 articoli in italiano
```

Esempio di front matter:

```yaml
---
title: "Consultazione ANAC sul Whistleblowing: Posizione del Centro Hermes"
date: 2015-03-16T09:13:07Z
slug: "consultazione-anac-sul-whistleblowing-posizione-del-centro-hermes"
categories: ["News", "Press"]
tags: ["anac", "anticorruzione", "globaleaks", "transparency-international", "whistleblowing"]
draft: false
author: "Hermes Center"
source_url: "https://www.hermescenter.org/consultazione-anac-sul-whistleblowing-..."
source_live_url: "https://hermescenter.org/consultazione-anac-sul-whistleblowing-..."
language: it
images: ["anac-logo-300x68.jpg"]
attachments:
  - file: "ur104---whistleblowing.16.03.15_distributed.pdf"
    original_url: "http://www.anticorruzione.it/portal/rest/..."
    note: "PDF incompleto: la copia d'archivio è troncata"
---
```

I campi `source_url` e `source_live_url` servono a citare la fonte e a non creare contenuti
duplicati: conviene che gli articoli ripubblicati puntino all'originale su hermescenter.org,
con un `canonical` o una riga di attribuzione.

## Come importarlo

```bash
tar xzf hermes-globaleaks-hugo-20261103.tar.gz
rsync -a content/ /percorso/del/sito/content/
hugo server -D        # per controllare prima di pubblicare
```

Due cose da sapere:

1. **Se il sito usa l'altra convenzione multilingua**, cioè `index.it.md` dentro un'unica
   cartella invece di `content/it/`, i file vanno rinominati. Si fa in una riga:
   `for f in content/it/blog/*/index.md; do mv "$f" "${f%index.md}index.it.md"; done`
   e poi si spostano le cartelle sotto `content/blog/`.
2. **Le immagini** sono dentro i bundle, non in `assets/images/blog/` come quelle attuali del
   sito. Hugo le elabora comunque, essendo risorse della pagina; se preferite la cartella
   condivisa, vanno spostate e i link aggiornati.

## Contenuto

- **67 articoli**: 24 in inglese, 43 in italiano, dal 2008 al 2024
- **33 allegati**: 11 documenti e 22 immagini
- **5 articoli** hanno una nota in coda che segnala allegati non integri

Temi riconosciuti: GlobaLeaks 59, whistleblowing 46, anticorruzione 20,
Transparency International 15, ANAC 11. L'elenco completo, con data, titolo, temi e numero di
allegati, è in `INDICE.csv` e in `indice.json`.

## Qualità dei dati

Gli articoli provengono da una copia d'archivio della Wayback Machine, quindi:

- **8 documenti** dell'archivio complessivo erano stati troncati a 1 MB dal crawler; quelli che
  finiscono in questa selezione sono segnalati con `note:` nel front matter e con una nota in
  coda all'articolo. Sono stati tenuti perché una parte del documento è meglio di niente.
- Alcuni allegati non sono mai stati recuperati, né dall'archivio né dai siti d'origine: anche
  questi sono dichiarati nella nota in coda.
- I documenti di terzi (ANAC, Garante, EDRi e altri) sono inclusi come copia locale, perché
  i link originali in molti casi non rispondono più.

I testi restano di Hermes Center; verificate la licenza con loro prima della ripubblicazione.
