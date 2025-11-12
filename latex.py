import os
import subprocess
import shutil
import tempfile
from pathlib import Path

# Chemin vers TeXLivePortable/bin
import sys

base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
TEXLIVE_PATH = os.path.join(base_path, "TeXLivePortable", "bin", "windows")  
os.environ["PATH"] = TEXLIVE_PATH + os.pathsep + os.environ["PATH"]



import os
import subprocess
import shutil
from pathlib import Path

def compiler_latex(plaquette_json, nom_fichier, dossier_compilation, dossier_sortie_absolu, ):
    
    fichier_tex = nom_fichier + '.tex'
    nom_fichier_pdf = nom_fichier + '.pdf'
    print(f"📄 Compilation de : {fichier_tex}")

    dossier_compilation = Path(dossier_compilation)
    dossier_compilation.mkdir(parents=True, exist_ok=True)

    # Créer le fichier .tex dans le dossier de compilation
    tex_path = dossier_compilation / fichier_tex
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(plaquette_text(plaquette_json))
        
    # Copier logo.png (et autres ressources) si nécessaire
    dossier_script = Path(__file__).parent
    ressources = ["mon_style.sty"]  # Ajoute ici tous les fichiers nécessaires

    for nom_fichier in ressources:
        source = dossier_script / nom_fichier
        destination = dossier_compilation / nom_fichier
        if source.exists():
            shutil.copy2(source, destination)
        else:
            print(f"⚠️ Fichier manquant : {nom_fichier}")


    # Compiler
    try:
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", fichier_tex],
            cwd=dossier_compilation,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Nettoyage des fichiers auxiliaires
        for ext in [".aux", ".log", ".out", ".toc", ".tex"]:
            fichier = dossier_compilation / fichier_tex.replace(".tex", ext)
            if fichier.exists():
                fichier.unlink()

        if result.returncode == 0:
            print("✅ Compilation réussie.")

            # Déplacer le PDF
            pdf_path = dossier_compilation / fichier_tex.replace(".tex", ".pdf")
            destination = Path(dossier_sortie_absolu) / nom_fichier_pdf
            destination.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(pdf_path, destination)
            print(f"📁 PDF final déplacé dans : {destination}")
            return destination

        else:
            print("❌ Erreur LaTeX :")
            print(result.stdout)
            print(result.stderr)
            return None
    except FileNotFoundError:
        print("⚠️ Erreur : xelatex introuvable. Vérifie ton installation.")


def generer_sommaire(plaquette_json):
    AG = []
    lines = []
    AG_type = None
    for key, value in plaquette_json.items():
        if key != "Structure" and isinstance(value, dict):
            for section, section_content in value.items():
                # Ex: "Approbation des comptes", etc.

                has_documents = False
                section_lines = [f"\\subsection*{{{section}}}"]

                for sub_section, documents in section_content.items():
                    # Ex : Assemblée générale
                    # documents est un dict avec les noms des documents
                    doc_lines = []

                    for doc_title, is_present in documents.items():
                        if is_present:
                            doc_lines.append(f"\\item {doc_title}")
                            
                            AG_type = key  # "AGO" ou "AGE"

                    if doc_lines:
                        section_lines.append(f"\\subsubsection*{{{sub_section}}}")
                        section_lines.append("\\begin{LeftLineBox}")
                        section_lines.append("\\begin{itemize}[label={}, leftmargin=0.75em, itemsep=0.5pt, parsep=0pt, topsep=0pt]")
                        section_lines.extend(doc_lines)
                        section_lines.append("\\end{itemize}")
                        section_lines.append("\\end{LeftLineBox}")
                        has_documents = True

                if has_documents:
                    lines.extend(section_lines)
                    section_title = section.upper()
                    AG.append(f"{section_title} \\\\")
                    
            if AG_type == "AGO":
                if len(AG) > 1 :
                    titles = ["ASSEMBLÉES GÉNÉRALES ORDINAIRES \\\\"]
                else:
                    titles = ["ASSEMBLÉE GÉNÉRALE ORDINAIRE \\\\"]
                titles.extend(AG)
            else :
                titles = ["ASSEMBLÉE GÉNÉRALE EXTRAORDINAIRE \\\\"]
                titles.extend(AG)
                titles.append(f"""{plaquette_json["Structure"]["Date de l'AGE"]} \\\\""")
    return "\n".join(titles), "\n".join(lines)


def plaquette_text(plaquette_json):
    structure = plaquette_json["Structure"]
    forme_juridique = structure["Forme Juridique"]
    raison_sociale = structure["Raison sociale"]
    capital = structure["Capital social"]
    adresse = structure["Adresse"]
    rue = adresse["Rue"]
    code_postal = adresse["Code postal"]
    ville = adresse["Ville"]
    exercice_clos = structure["Exercice clos le"]
    exercice_comptable = structure["Exercice comptable"]

    titles, sommaire = generer_sommaire(plaquette_json)

    return f"""

\\documentclass[12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{graphicx}}
\\usepackage{{xcolor}}
\\usepackage{{titlesec}}
\\usepackage{{setspace}}
\\usepackage{{geometry}}
\\usepackage{{fontspec}}
\\usepackage{{tikz}}
\\usepackage{{enumitem}}
\\usepackage[most]{{tcolorbox}}
\\usepackage{{eso-pic}}


\\geometry{{top=2.5cm, bottom=2.5cm, left=2.5cm, right=2.5cm}}


\\definecolor{{lightgray}}{{gray}}{{0.6}} % gris clair (modifiable)

\\newtcolorbox{{GrayBottomBox}}{{
  enhanced,
  colback=white,
  colframe=white,
  boxrule=0pt,
  coltitle=black,
  borderline south={{1.5pt}}{{-4pt}}{{lightgray}}, % ligne grise en bas
  left=0pt,
  right=0pt,
  top=2pt,
  bottom=2pt,
  boxsep=0pt,
  width=\linewidth,
  sharp corners
}}


\\newtcolorbox{{LeftLineBox}}[1][]{{%
  enhanced,
  colframe=white,
  colback=white,
  boxrule=0pt,
  left=4pt,
  right=0pt,
  top=0pt,
  bottom=0pt,
  borderline west={{2.5pt}}{{4pt}}{{blue}},
  sharp corners,
  boxsep=0pt,
  #1
}}



% Définitions des polices
\\setmainfont{{Times New Roman}}
\\newfontfamily\\vlads{{Vladimir Script}}

% Couleurs
\\definecolor{{bleu}}{{RGB}}{{0,0,139}}
\\definecolor{{rouge}}{{RGB}}{{178,34,34}}

% Commandes personnalisées
\\newcommand{{\\rougemaj}}[1]{{\\textcolor{{rouge}}{{\\vlads{{\\MakeUppercase{{#1}} }}}}}}
\\newcommand{{\\bleutexte}}[1]{{\\textcolor{{bleu}}{{#1}} }}

% Commande pour le mot "Expertise Comptable des Monts d'Or"
\\newcommand{{\\cabinetname}}{{
    {{\\fontsize{{36}}{{42}}\\selectfont\\vlads\\textcolor{{red}}{{E}}}}%
    \\textbf{{{{\\fontsize{{20}}{{24}}\\selectfont\\textcolor{{bleu}}{{xpertise }}}}}}%
    {{\\fontsize{{36}}{{42}}\\selectfont\\vlads\\textcolor{{red}}{{C}}}}%
    \\textbf{{{{\\fontsize{{20}}{{24}}\\selectfont\\textcolor{{bleu}}{{omptable des }}}}}}%
    {{\\fontsize{{36}}{{42}}\\selectfont\\vlads\\textcolor{{red}}{{M}}}}%
    \\textbf{{{{\\fontsize{{20}}{{24}}\\selectfont\\textcolor{{bleu}}{{onts d’}}}}}}%
    {{\\fontsize{{36}}{{42}}\\selectfont\\vlads\\textcolor{{red}}{{O}}}}%
    \\textbf{{{{\\fontsize{{20}}{{24}}\\selectfont\\textcolor{{bleu}}{{r}}}}}}%
}}

\\begin{{document}}

\\pagestyle{{empty}}

\\begin{{center}}
\\vspace*{{2cm}}

\\textbf{{ \\fontsize{{20}}{{24}}\\selectfont {titles}}}

\\vspace*{{4cm}}
\\bleutexte{{\\textbf{{ \\fontsize{{16}}{{20}}\\selectfont {raison_sociale} }} }}\\\\
{forme_juridique} au capital de {capital} euros\\\\
{rue}\\\\
{code_postal} {ville}\\\\

\\vspace{{3cm}}
Exercice clos le {exercice_clos}\\\

\\vspace{{3cm}}

\\begin{{center}}
    {{\\cabinetname \\par}}
    \\vspace{{0.5cm}}  % Espace après le nom du cabinet

    {{\\fontsize{{10}}{{12}}\\selectfont\\bfseries\\MakeUppercase{{2 Rue de la Chèvre}} \\par}}
    {{\\fontsize{{10}}{{12}}\\selectfont\\bfseries\\MakeUppercase{{69370 Saint-Didier-au-Mont-d'Or}} \\par}}


    \\vspace{{0.3cm}}  % Même espace que précédemment

    {{\\fontsize{{8}}{{10}}\\selectfont Tél. : 04.23.52.55.23 \\par}}
    {{\\fontsize{{8}}{{10}}\\selectfont contact@cabinet-ecmo.com \\par}}
\\end{{center}}

\\end{{center}}

\\newpage


\\AddToShipoutPictureBG*{{%
  \\put(\\LenToUnit{{\\dimexpr\\paperwidth - 3.5cm}},\\LenToUnit{{\\paperheight - 3.5cm}}){{%
    \\includegraphics[width=3cm,height=3cm]{{logo.png}}%
  }}%
}}



\\section*{{Sommaire}}

\\begin{{GrayBottomBox}}
\\textbf{{{forme_juridique} {raison_sociale}}}\\
\\end{{GrayBottomBox}}
\\noindent \\textbf{{{exercice_comptable}}}


{sommaire}

\\end{{document}}


"""


