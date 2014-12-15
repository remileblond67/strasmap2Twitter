#!/usr/bin/python
# -*- coding: utf8 -*-
#--------------------------------------------------------------------------------------
# eCarto : publication en continu des alertes SIRAC sur le compte Twitter de Strasbourg
#--------------------------------------------------------------------------------------
import sys
import tweepy
import httplib
import json
import urllib2
import pickle
import time
import hashlib

class config:
    "Lecture du fichier de configuration"
    def __init__(self):
        print ("Lecture du fichier de configuration")
        self.config={}
        try:
            configFile = open('configTwitter.conf', 'rb')
        except:
            self.msg.erreur ("Impossible de trouver le fichier de configuration")
        lines = configFile.readlines()
        
        for line in lines:
            sp = line.split('#')[0]
            sp = sp.split('=')
            
            if len(sp)==2:
                self.config[sp[0].strip()] = sp[1].strip()
                
        configFile.close()
        
    def val(self, clef):
        try:
            return self.config[clef]
        except:
            self.msg.erreur ("Variable inconnue")
        

class compteTwitter:
    "Manipulation du compte Twitter"
    def __init__(self):
        self.msg = outils()
        
        myConfig = config()

        self.msg.liste ("Initialisation de la connexion à Twitter")
        
        CONSUMER_KEY = myConfig.val("CONSUMER_KEY")
        CONSUMER_SECRET = myConfig.val("CONSUMER_SECRET")
        ACCESS_KEY = myConfig.val("ACCESS_KEY")
        ACCESS_SECRET = myConfig.val("ACCESS_SECRET")
        
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
        self.api = tweepy.API(auth)

        # Identification du mode de lancement
        if len(sys.argv) < 2:
            self.msg.erreur("Précisez une action en paramètre ('cont' ou 'jour')")
            sys.exit(1)
        else:
            if (sys.argv[1] == "cont"):
                self.mode = 'cont'
            elif (sys.argv[1] == "jour"):
                self.mode = 'jour'
            else:
                self.msg.erreur("Mode "+sys.argv[1]+" non supporté")
                exit(1)

        if (self.mode == 'cont'):
            self.msg.info ("Mode continu - prise en compte de l'historique")
            try:
                histoTweetFile = open("ecart_alerte_historique.pkl", 'rb')
                self.histoTweet = pickle.load(histoTweetFile)
                histoTweetFile.close()
            except:
                self.msg.info("Aucun historique à charger - Initialisation d'un nouvel historique")
                self.histoTweet = {}
        elif (self.mode == 'jour'):
            self.msg.info ("Mode journalier - pas d'historique")
            self.histoTweet = {}

    def __del__(self):
        try:
            histoTweetFile = open("ecart_alerte_historique.pkl", 'wb')
            pickle.dump(self.histoTweet, histoTweetFile, -1)
            histoTweetFile.close()
        except:
            self.msg.erreur ("Impossible de sauvegarder l'historique")

    def publie(self, titre, texte):
        "Publication d'un Tweet"
        finalLong = "\n#inforouteSIRAC\nhttp://carto.strasmap.eu/trafic_alert"
        finalCourt = "\n#inforouteSIRAC"

        #if (self.mode == "jour"):
        #    titre = "Rappel : " + titre

        if (len(titre + texte + finalLong) < 137) :
            message = titre + " - " + texte + finalLong
        else:
            if (len(titre + texte + finalCourt) < 137):
                message = titre + " - " + texte + finalCourt
            else:
                message = titre + " - " + texte
        
        # Publication du Tweet s'il n'a pas déja été publié dans les 24 dernières heures
        self.msg.tweet(message)
 
        if (self.mode == "cont"):
            try:
                delai = float(time.time()) - float(self.histoTweet[message])
            except:
                delai = 90000;
                self.msg.info ("  Pas d'historique trouvé pour ce message")
        else:
            delai = 90000;

        if ((delai) > 86400) :
            try:
                self.api.update_status(message[:140])
                self.msg.liste("Publication de '"+titre+"' (longueur : "+ str(len(message))+ ")")
                self.histoTweet[message] = time.time()
            except:
                self.msg.liste ("Tweet '" + titre + "' en double -> refus par Twitter")
        else:
            self.msg.liste ("Ce message a déjà été publié il y a %d minutes -> Aucune action" % int(delai / 60))

class fluxSirac:
    "Recuperation des alertes SIRAC a partir du flux StrasMap"
    def __init__(self):
        self.msg = outils()
        self.msg.liste("Ouverture du flux SIRAC")
        self.tweet = compteTwitter()
        self.fluxJson = urllib2.urlopen('http://carto.strasmap.eu/remote.amf.json/TraficAlert.status')

    def chargeEvt(self):
        self.msg.liste("Récupération des alertes à partir du flux StrasMap")
        alertes = json.load(self.fluxJson)
        
        for alerte in alertes['s']:
            #if (alerte['evt_carto'] == 'true') :
                # print ('  Coord. Tweet : ' + alerte['x'] + ' ' + alerte['y'])
            if (alerte['evt_liste'] == 'true'):
                self.tweet.publie(alerte['dt'], alerte['dp'])

class outils:
    "Outils transversaux"
    def __init__(self):
        self.largeur = 110

    def titre(self, message):
        "Titre principal"
        longueur = len(message)
        marge = (self.largeur - longueur)/2 - 1
        print ("-" * self.largeur)
        print (" " * marge + message)
        print ("-"*self.largeur)

    def soustitre(self, message):
        "Sous-titre"
        print ("\n" + " " * ((self.largeur - len(message))/2) + "--- "+message+" ---")

    def liste(self, message):
        "Message standard"
        print ("- " + message)

    def erreur(self, message):
        "Message d'erreur"
        msg = "ERREUR : " + message
        print ("!" * len(msg))
        print msg
        print ("!" * len(msg))

    def info(self, message):
        "Message d'information"
        print ("INFO : " + message)

    def tweet(self, message):
        "Affichage du contenu d'un Tweet"
        titre = "CONTENU DU TWEET"
        print ("\n" + "-" * (self.largeur - len(titre) - 2) + titre + " -")
        print (message)
        print ("-" * self.largeur)


# Lancement du traitement
msg = outils()
msg.titre("Publication des alertes SIRAC dans Twitter")
flux = fluxSirac()
flux.chargeEvt()
msg.soustitre("Fin du traitement")
