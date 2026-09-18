# hermescenter.org: ripristino dell'archivio News & Press (2008–2024)

Questo repository ricostruisce gli articoli **News & Press** del vecchio sito hermescenter.org, che non sono più online dal passaggio al sito attuale (2024). Ha due obiettivi:

1. **Revisione.** Il sito HTML statico in `site/` serve alla revisione da parte di terzi e alla stampa, prima di decidere cosa ripubblicare.
2. **Ripubblicazione.** In `data/` e `media/` ci sono i dati grezzi pronti per l'import nel WordPress attuale: testi, metadati, categorie, tag, immagini e allegati.

> Stato: **in revisione**. Nulla è ancora stato pubblicato sul sito nuovo.

## Contenuto

| Cartella | Cosa contiene |
|---|---|
| `site/` | Sito statico di revisione. Contiene l'indice con le categorie e una scheda per ogni articolo. `site/stampa.html` è il dossier con tutti gli articoli, pronto da stampare. |
| `data/posts.json`, `data/posts.csv` | Un record per articolo: titolo, data, URL originale, categorie, tag, allegati. |
| `data/posts/<id>/post.json` | I metadati del singolo articolo. `<id>` è lo slug originale; per gli articoli `/it/` diventa `it__<slug>`. |
| `data/posts/<id>/content.html` | Il testo dell'articolo, con i **link nella forma originale** (URL assoluti). |
| `data/categories.json`, `data/tags.json` | Categorie e tag, con il numero di articoli per ciascuno. |
| `data/media.json` | Ogni file usato: percorso nel repo, URL originale, tipo, dimensione, sha256, articoli che lo usano. |
| `data/missing.json` | Allegati che non è stato possibile recuperare. |
| `media/wp-content/uploads/…` | Immagini e documenti caricati da Hermes, **nello stesso percorso che avevano sul sito**. |
| `media/external/<host>/…` | Documenti di terzi linkati dagli articoli (Garante, ANAC, EDPB, EDRi…), da ospitare sul sito di Hermes. |
| `tools/` | Gli script che hanno generato tutto questo, per trasparenza e riproducibilità. |

## Come fare la revisione

1. Scarica il repository (**Code → Download ZIP**) e apri `site/index.html` nel browser. Non serve un server.
2. Per ogni articolo scegli **Ripristina**, **Da valutare** o **No**, e se serve aggiungi una nota. Puoi farlo dall'indice o dalla scheda dell'articolo.
3. Le scelte restano salvate **solo nel browser** che stai usando. Alla fine premi **Esporta CSV** e invia il file. **Importa CSV** serve a riprendere il lavoro su un altro computer.
4. Per la stampa apri `site/stampa.html` e usa *Stampa → Salva come PDF*. Ogni articolo parte su una pagina nuova. Anche l'indice e le singole schede sono stampabili.

## Principi per la ripubblicazione

- **Date originali.** Ogni articolo conserva la data di pubblicazione originale:
  - `date_gmt` (UTC) corrisponde al campo `post_date_gmt` di WordPress;
  - `date_europe_rome` corrisponde a `post_date`.
- **URL originali.** Ogni articolo torna al suo indirizzo originale, `path`: per esempio `/alac-anticorruzione-whistleblowing-hermes/` diventa lo slug di WordPress con i permalink `/%postname%/`. Nessuno di questi slug è oggi usato sul sito nuovo. Gli indirizzi alternativi elencati in `old_urls` vanno reindirizzati con un 301. Per i 6 articoli `/it/` bisogna decidere se mantenere il prefisso `/it/`.
- **Stessi URL per i file.** I file in `media/wp-content/uploads/` vanno copiati sul server nello **stesso percorso**, così i vecchi link continuano a funzionare. Poi vanno registrati nella Media Library senza essere spostati, per esempio con `wp media import --skip-copy`.
- **Documenti di terzi ospitati in locale.** Ogni documento linkato di cui abbiamo una copia viene pubblicato su hermescenter.org. Il link nell'articolo va riscritto sulla copia locale, citando l'URL originale come fonte. Il percorso di destinazione è ancora da decidere; una proposta è `/wp-content/uploads/archivio/<host>/…`. In `content.html` i link restano quelli originali: la corrispondenza URL originale → file è in `data/media.json`.
- **Categorie.** Tutte le categorie sono quelle che il vecchio sito mostrava sotto ogni articolo:

  | Categoria | Articoli | Nota |
  |---|---|---|
  | News | 132 | |
  | Press | 95 | Era una sottocategoria di News |
  | /it/ | 6 | Categoria nuova per gli articoli della vecchia sezione italiana |
  | Uncategorized | 5 | Da decidere |
  | Newsletter | 2 | Da decidere |

  I tag (31) sono in `data/tags.json`.

## Allegati non recuperabili

Questi 7 documenti non esistono più né nell'archivio Wayback né sul sito attuale. Se qualcuno in Hermes ha gli originali, vanno aggiunti in `media/` allo stesso percorso.

- `wp-content/uploads/2015/05/2015_05_14_workshop.pdf`, `2015_05_18_Vicino-Lontano_Diego.pdf`
- `wp-content/uploads/2017/11/GlobaLeaksOpenSourcePA.pdf`
- `wp-content/uploads/2018/02/WB.pdf`
- `wp-content/uploads/2018/02/151203-Service-Agreement-Smartmatic-…-SMMT.doc`
- `wp-content/uploads/2018/02/Rodolfi_Il-ruolo-del-whistleblowing-nella-cybersecurity_v3-1.docx`
- `wp-content/uploads/2021/09/EURODAC-open-letter.pdf` (è un documento EDRi)

L'elenco aggiornato, con l'articolo di riferimento per ciascun file, è in `data/missing.json`.

## Provenienza dei dati

- **Fonte principale:** un crawl dell'Internet Archive (Wayback Machine) del vecchio sito.
- **Link esterni:** dove il crawl aveva alterato un link esterno, l'URL originale è stato recuperato dalla copia grezza (`id_`) dello stesso articolo su Wayback, confrontando i link uno per uno.
- **File sostituiti:** le copie non valide nello zip (pagine di errore salvate al posto dei PDF) sono state sostituite con i file scaricati dall'originale.
- **Documenti di terzi:** i documenti esterni appartengono ai rispettivi autori e sono conservati qui solo per mantenere funzionanti i riferimenti degli articoli.
