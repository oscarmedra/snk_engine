"""Donne le genre d'un nom français, pour que le moteur pose le bon article.

Le soninké marque la détermination par `ke` ; le français, lui, a besoin du genre
pour choisir entre « un » et « une ». C'est une question de français, pas de
soninké : rien ici ne touche à la langue du locuteur.

Les terminaisons décident de la plupart des cas. Le reste est une liste explicite,
parce qu'une règle qui se trompe une fois sur cinq ne vaut rien et qu'il n'y a
aucune honte à écrire ce qu'on sait.
"""

import re

# les mots que les terminaisons classeraient mal
EXCEPTIONS = {
    # féminins qu'une terminaison dirait masculins
    "eau": "f", "peau": "f", "main": "f", "fin": "f", "faim": "f", "soif": "f",
    "dent": "f", "jument": "f", "nuit": "f", "mort": "f", "part": "f", "dot": "f",
    "forêt": "f", "clef": "f", "nef": "f", "croix": "f", "voix": "f", "noix": "f",
    "paix": "f", "toux": "f", "souris": "f", "brebis": "f", "perdrix": "f",
    "fois": "f", "loi": "f", "foi": "f", "mer": "f", "chair": "f", "cour": "f",
    "tour": "f", "soeur": "f", "sœur": "f", "fleur": "f", "peur": "f", "douleur": "f",
    "chaleur": "f", "couleur": "f", "odeur": "f", "sueur": "f", "vapeur": "f",
    "faveur": "f", "rumeur": "f", "tumeur": "f", "valeur": "f", "saveur": "f",
    # masculins qu'une terminaison dirait féminins
    "livre": "m", "arbre": "m", "verre": "m", "ventre": "m", "centre": "m",
    "sucre": "m", "cuivre": "m", "beurre": "m", "tonnerre": "m", "lierre": "m",
    "fleuve": "m", "rêve": "m", "groupe": "m", "principe": "m", "type": "m",
    "squelette": "m", "silence": "m", "espace": "m", "service": "m", "exercice": "m",
    "sacrifice": "m", "office": "m", "commerce": "m", "divorce": "m", "mélange": "m",
    "village": "m", "visage": "m", "voyage": "m", "ouvrage": "m", "héritage": "m",
    "musée": "m", "lycée": "m", "trophée": "m", "incendie": "m", "génie": "m",
    "parapluie": "m", "foie": "m", "sourire": "m", "navire": "m", "empire": "m",
    "problème": "m", "système": "m", "poème": "m", "thème": "m", "programme": "m",
    "crime": "m", "régime": "m", "rhume": "m", "costume": "m", "légume": "m",
    "volume": "m", "parfum": "m", "doute": "m", "compte": "m", "conte": "m",
    "piège": "m", "siège": "m", "collège": "m", "privilège": "m", "manège": "m",
    "squale": "m", "pétale": "m", "scandale": "m", "intervalle": "m",
    "silence": "m", "sable": "m", "meuble": "m", "câble": "m", "peuple": "m",
    "temple": "m", "exemple": "m", "angle": "m", "oncle": "m", "spectacle": "m",
    "miracle": "m", "obstacle": "m", "article": "m", "cercle": "m", "couple": "m",
}

# Le genre des gloses que les terminaisons ne tranchent pas. Écrit à la main :
# c'est du français, pas du soninké, et une règle qui hésite ne vaut pas une liste.
GLOSES = {
    "adultère": "m", "aile": "f", "albinos": "m", "amende": "f", "ami": "m",
    "aumône": "f", "automobile": "f", "autruche": "f", "aveugle": "m", "bague": "f",
    "baobab": "m", "baptême": "m", "barbe": "f", "biche": "f", "bien": "m",
    "branche": "f", "cadavre": "m", "calebasse": "f", "cauri": "m", "cause": "f",
    "cendre": "f", "champ personnel": "m", "chapitre": "m", "chimpanzé": "m",
    "chronique historique": "f", "cigogne": "f", "ciseaux": "m", "cloche": "f",
    "clé": "f", "consonne": "f", "coq": "m", "corne": "f", "coutume": "f",
    "couvercle": "m", "crapaud": "m", "crocodile": "m", "célibataire": "m",
    "datte": "f", "dos": "m", "drap": "m", "dromadaire": "m", "ecole": "f",
    "ecrevisse": "f", "elève": "m", "enclos": "m", "enclume": "f", "endroit": "m",
    "ennemi": "m", "epine": "f", "esprit": "m", "etudiant coranique": "m",
    "farine": "f", "fenêtre": "f", "feuille": "f", "fille": "f", "fils aîné": "m",
    "flamme": "f", "flirt": "m", "flèche": "f", "flûte": "f", "flûtiste": "m",
    "force": "f", "front": "m", "fusil": "m", "geai": "m", "girafe": "f",
    "goitre": "m", "gombo": "m", "grâce divine": "f", "guerre": "f",
    "guêpe maçonne": "f", "génisse": "f", "herbe": "f", "honte": "f", "houe": "f",
    "iguane": "m", "ile": "f", "jambe": "f", "jeune fille": "f", "légende": "f",
    "mardi": "m", "mare": "f", "mari": "m", "marmite": "f", "mensonge": "m",
    "molaire": "f", "moustiquaire": "f", "mère": "f", "natte": "f", "nid": "m",
    "noble": "m", "nombril": "m", "oeuf": "m", "os": "m", "passeport": "m",
    "peul": "m", "photo": "f", "pipe": "f", "poche": "f", "poitrine": "f",
    "porte": "f", "porte monnaie": "m", "prince": "m", "prix": "m", "proverbe": "m",
    "père": "m", "queue": "f", "quinquéliba": "m", "roi": "m", "sabre": "m",
    "salive": "f", "servante": "f", "singe": "m", "souci": "m", "souhait": "m",
    "sourd": "m", "syllabe": "f", "termite": "m", "thé": "m", "toit": "m",
    "tête": "f", "varan": "m", "variole": "f", "vendredi": "m",
}

FEMININES = ("tion", "sion", "xion", "aison", "té", "tié", "ée", "ie", "ure",
             "ance", "ence", "esse", "ette", "elle", "eille", "ade", "aine",
             "euse", "trice", "ude", "ière", "ode", "ose", "ance", "andre")
MASCULINS = ("age", "ment", "eau", "ier", "isme", "oir", "eil", "ail", "at",
             "et", "ot", "ou", "al", "ain", "ant", "ent", "in", "on", "eur",
             "er", "is", "us", "as", "if", "ac", "ic", "oc", "uc", "ard", "au")

# les gloses qui ne sont pas des noms : un adjectif ne prend pas d'article ici
ADJECTIFS = {
    "riche", "pauvre", "avare", "jeune", "vieux", "bleu", "rouge", "vert", "jaune",
    "noir", "blanc", "mauvais", "bon", "grand", "petit", "long", "court", "lourd",
    "léger", "chaud", "froid", "sale", "propre", "cher", "facile", "difficile",
    "beau", "laid", "fort", "faible", "plein", "vide", "dur", "mou", "sec",
    "autre", "eloigné", "éloigné", "peureux", "très gros", "gros", "maigre",
    "egal", "égal", "premier", "un certain", "frais", "certain",
}


def est_adjectif(glose: str) -> bool:
    return glose.strip().lower() in ADJECTIFS


def genre(nom: str) -> str | None:
    """« m », « f », ou None quand ni la liste ni les terminaisons ne tranchent."""
    mot = nom.strip().lower()
    mot = re.sub(r"^(le |la |les |l'|un |une |du |de la |des )", "", mot)
    if mot in GLOSES:
        return GLOSES[mot]
    dernier = mot.split()[-1] if mot.split() else mot
    if dernier in EXCEPTIONS:
        return EXCEPTIONS[dernier]
    for fin in sorted(FEMININES, key=len, reverse=True):
        if dernier.endswith(fin):
            return "f"
    for fin in sorted(MASCULINS, key=len, reverse=True):
        if dernier.endswith(fin):
            return "m"
    # un nom en -e sans autre indice est plus souvent féminin, mais « plus souvent »
    # ne suffit pas : mieux vaut s'abstenir et laisser le mot de côté
    return None

# Le glossaire a perdu ses accents en chemin, et le moteur ne doit pas publier
# « un etrier ». Corrections d'orthographe française, rien de plus.
ORTHOGRAPHE = {
    "alumette": "allumette", "echelle": "échelle", "ecole": "école",
    "ecrevisse": "écrevisse", "elève": "élève", "eléphant": "éléphant",
    "epine": "épine", "etrier": "étrier", "eventail": "éventail",
    "etudiant coranique": "étudiant coranique", "porte monnaie": "porte-monnaie",
    "oeuf": "œuf", "ile": "île", "foret": "forêt", "fenetre": "fenêtre",
}


def corriger(glose: str) -> str:
    bas = glose.strip().lower()
    return ORTHOGRAPHE.get(bas, bas)
