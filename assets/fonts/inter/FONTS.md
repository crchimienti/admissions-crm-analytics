**Language:** English · Español below

# Inter fonts used for the notebook charts

The two font files in this folder are the ones that drew the chart images of the frozen F1 notebook. They are loaded from this folder by [`scripts/notebook_rendering.py`](../../../scripts/notebook_rendering.py); nothing has to be installed on the system and nothing is downloaded.

| File | SHA-256 | Font version (name table) |
|---|---|---|
| `Inter-Regular.otf` | `be6d709dcb730ddaf050cbdae6fe89bd56d5d14dc66885639bbf6f06bd03521b` | Version 4.000;git-a52131595 |
| `Inter-Bold.otf` | `00fd6f4691ee8884a33b46bf45851b341927c37c30064f558e1befb242971c49` | Version 4.000;git-a52131595 |

- **Provenance.** Copied byte for byte from the reference environment, where they were installed by the Debian package `fonts-inter` version `4.0+ds-1` (`/usr/share/fonts/opentype/inter/`). Upstream project: Inter, by The Inter Project Authors, <https://github.com/rsms/inter>. The Debian package is built from the upstream source, so these files are not claimed to be byte-identical to the files of the upstream release archive.
- **Licence.** SIL Open Font License, Version 1.1, as stated in the fonts' own licence field (name ID 13). [`OFL.txt`](OFL.txt) is the upstream licence file `LICENSE.txt` of the Inter repository at tag `v4.0`, unchanged (SHA-256 `262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a`): copyright notice `Copyright (c) 2016 The Inter Project Authors` and the full SIL Open Font License 1.1. The fonts' own name table carries `Copyright 2016 The Inter Project Authors` and the trademark notice `Inter UI and Inter is a trademark of rsms`; the Debian package's copyright file declares `2016-2023 The Inter Project Authors`. The fonts are not modified. The project's own licence is a separate, pending decision and does not apply to these files.
- **Settings applied with them:** matplotlib's built-in defaults first (any user or site `matplotlibrc` is ignored), then `font.family = Inter, sans-serif, DejaVu Sans` and `text.hinting = no_hinting`.

---

# Fuentes Inter de los gráficos del notebook

Los dos archivos de fuente de esta carpeta son los que dibujaron las imágenes de los gráficos del notebook congelado de F1. Los carga desde esta carpeta [`scripts/notebook_rendering.py`](../../../scripts/notebook_rendering.py); no hay que instalar nada en el sistema y no se descarga nada.

- **Procedencia.** Copiados byte a byte del entorno de referencia, donde los instaló el paquete Debian `fonts-inter` versión `4.0+ds-1`. Proyecto original: Inter, de The Inter Project Authors, <https://github.com/rsms/inter>. El paquete Debian se construye desde el código fuente original, así que no se afirma que estos archivos sean idénticos byte a byte a los del archivo de publicación original.
- **Licencia.** SIL Open Font License, versión 1.1, como indica el campo de licencia de las propias fuentes. [`OFL.txt`](OFL.txt) es el archivo de licencia original `LICENSE.txt` del repositorio de Inter en la etiqueta `v4.0`, sin cambios (SHA-256 `262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a`): aviso `Copyright (c) 2016 The Inter Project Authors` y la licencia SIL Open Font License 1.1 completa. La tabla de nombres de las fuentes contiene `Copyright 2016 The Inter Project Authors` y el aviso de marca `Inter UI and Inter is a trademark of rsms`; el archivo de copyright del paquete Debian declara `2016-2023 The Inter Project Authors`. Las fuentes no se modifican. La licencia del proyecto es una decisión aparte, todavía pendiente, y no se aplica a estos archivos.
- **Ajustes aplicados con ellas:** primero los valores por defecto de matplotlib (se ignora cualquier `matplotlibrc` del usuario o del sistema) y después `font.family = Inter, sans-serif, DejaVu Sans` y `text.hinting = no_hinting`.
