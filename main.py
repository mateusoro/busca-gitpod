# -*- coding: utf-8 -*-
from requests_html import HTMLSession
from flask import Flask, request, render_template, redirect
import imdb
from bson.json_util import dumps
import pymongo
import dns
from imdbparser import IMDb
from pymongo import MongoClient
from guessit import guessit
from flask_socketio import SocketIO, emit
import logging
import threading
import os

import libtorrent as lt
import time

ses = lt.session()
params = { 'save_path': '/home/downloads/'}
ses.start_dht()

#https://www.btmulu.com/hash/
#ps -fA | grep main.py
#kill 509

session = HTMLSession()
app = Flask('app')
app.debug = False

ia = imdb.IMDb()
top = ia.get_top250_movies()
print(top[0])

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*", logger=False, engineio_logger=False)

client = MongoClient("mongodb+srv://root:root@cluster0-0rj95.mongodb.net/test?retryWrites=true")
db = client.registros

#db.registros.delete_many({'titulo' : "NOS4A2"})

def set_interval(func, sec):
	def func_wrapper():
		set_interval(func, sec)
		func()
	t = threading.Timer(sec, func_wrapper)
	t.start()
	return t

def automatico_ultimo():
	print('Automático Último Adicionado')
	socketio.start_background_task(thread_lista, 'https://ondeeubaixo.net/-', 5)

#set_interval(automatico_ultimo,60*20)
def carregar_sky(links):
	carregar_sky_forcar(links,False)

def carregar_sky_forcar(links,forcar):
	print('Início')
	global continuar
	socketio.emit('atualizar', 'Detalhes do Link')
	#links = db.magnets.find({'imdb': {'$ne': ''}})
	for l in links:
		if continuar:
			#print(db.registros.find({'magnet':l['link']}).count())
			#print(l['link'])
			li = l['link']
			try:
				ha = li[20:li.index('&')].lower()
			except:
				print("Erro Magnet: "+ li)
				ha = li[20:].lower()

			if len(l['imdb']) > 0 and (db.registros.find({'magnet':l['link']}).count()==0 or forcar) and db.legendado.find({'magnet':ha}).count()==0:
				socketio.emit('atualizar','Carregando: https://btdb.eu/torrent/' + ha)
				r = session.get('https://btdb.eu/torrent/' + ha)
				arquivos = r.html.find('.torrent-file-list tr')

				ingles = ''
				titulo = 'Não Encontrado'

				if len(arquivos)>0:

					#print(1)
					titulo = r.html.find("title", first=True).text
					#print(r.html.text)
					ingles = r.html.find('td:contains("LANGUAGE:United States")', first=True)
					if "DUAL" in titulo or "DUBLADO" in titulo:
						ingles = None
					teste1 = r.html.find('.file-name:contains("DUB")', first=True)
					teste2 = r.html.find('.file-name:contains("DUAL")', first=True)
					teste3 = r.html.find('.file-name:contains("Dub")', first=True)
					teste4 = r.html.find('.file-name:contains("Dual")', first=True)

					if teste1 != None or teste2 != None or teste3 != None or teste4 != None:
						ingles = None

				else:
					arquivos = carregar_torrent_download(li)
					for t in arquivos:
						if "DUAL" in t:
							ingles = None
						if "DUB" in t:
							ingles = None
						if "Dub" in t:
							ingles = None
						if "Dual" in t:
							ingles = None


				if ingles == None:

					ind = 0
					for a in arquivos:

						if type(a) is str:
							ar = a
							texto = ar
						else:
							ar = a.find('td')[1].text
							texto = ar


						texto = texto.replace('[WWW.BLUDV.TV] ', '').replace(
						'Acesse o ORIGINAL WWW.BLUDV.TV ', '').replace(
							'[ACESSE COMANDOTORRENTS.COM] ', '').replace(
								'WWW.COMANDOTORRENTS.COM', '').replace(
									'WWW.BLUDV.TV', '').replace(
										'[WW.BLUDV.TV]', '').replace('WwW.LAPUMiAFiLMES.COM', '').replace('x264', '').replace('h264', '')
						try:

							if (texto[-3:] not in ['exe', 'txt', 'url', 'srt', 'peg', 'jpg','png','nfo', 'zip']) and (texto[-10:] not in ['sample.mkv']) and (ar not in ["COMANDOTORRENTS.COM.mp4", "BLUDV.TV.mp4", "BLUDV.mp4","LAPUMiA.mp4","File Name"]) and ("LEGENDADO" not in texto):

								convert = guessit(texto)

								print('season' in convert)
								if 'season' in convert:
									sessao = str(convert['season'])

									if str(convert['season']) == "[2, 1]":
										sessao = "1"
									episode = str(convert['episode'])
									if episode == "[1, 2]":
										episode = "1"
									im = l['imdb'] + " " + sessao + " " + episode
									print(im)
									ins = {
									'id': 0,
									'imdb': im,
									'magnet': li,
									'mapa': ind,
									'nome': texto
									}
									db.registros.insert_one(ins)
									print(im, ind, convert['title'], texto)
									if ('NOS4A2' in texto) or ('nos4a2' in texto):
										socketio.emit('atualizar', 'Adicionado:  NOS4A2 (' + im + ") "+ texto)
									else:
										socketio.emit('atualizar', dumps(ins))
								else:
									ins = {'id': 0,'imdb': l['imdb'],'magnet': li,'mapa': ind,'nome': texto}
									db.registros.insert_one(ins)
									socketio.emit(
									'atualizar', dumps(ins))
									print(l['imdb'], ind, convert['title'], texto)

						except:
							print('Erro')

						ind = ind + 1
				else:
					ins = {'magnet': ha}
					db.legendado.insert_one(ins)
					socketio.emit('atualizar', 'Legendado ' + titulo +': https://btdb.eu/torrent/' + ha)
			else:
				print('link encontrado')

	socketio.emit('atualizar', 'Fim da Busca')
	limpar()

def carregar_torrent_download(link):
	r=[]
	handle = lt.add_magnet_uri(ses, link, params)

	contador = 0
	while (not handle.has_metadata() and contador < 20):
		print("Esperando "+str(contador))
		contador += 1
		time.sleep(1)

	if handle.has_metadata():
		torinfo = handle.get_torrent_info()

		for x in range(torinfo.files().num_files()):
			r.append(torinfo.files().file_path(x))
			print(torinfo.files().file_path(x))

		ses.remove_torrent(handle)
	return r

def limpar():
	for r in db.registros.find({"$or":[{"nome": {"$regex":"\.srt|\.url|\.exe|\.sub|\.txt|\.nfo|\.jpeg|\.jpg|\.png|\.zip|sample"}}, {"nome": "BLUDV.TV.mp4"}, {"nome": "BLUDV.mp4"},{"nome": "LAPUMiA.mp4"}, {"nome": "COMANDOTORRENTS.COM.mp4"}]}).limit(1000):
		nome = str(r['nome']).strip()
		db.registros.delete_one({"_id": r['_id']})
		print('Apagado: ', nome)

	for r in db.registros.aggregate([{'$group': {'_id': {'mapa': "$mapa",'magnet': "$magnet"},'uniqueIds': {'$addToSet': "$_id"},'count': {'$sum': 1}}},{'$match': {'count': {"$gt": 1}}}]):
		for x in range(0, len(r['uniqueIds']) - 1):
			id = r['uniqueIds'][x]
			db.registros.delete_one({"_id": id})
			print('Duplicado: ', r['uniqueIds'])
	db.registros.delete_many({'ano': {'$lt': 1989}})
	db.registros.delete_many({"mapa": {'$type': "string"}})
	corrigir_titulo_serie()
	corrigir_titulo_filme()


def corrigir_titulo_filme():
	print('corrigir_titulo_filme: Iniciado')
	repetir = False
	for r in db.registros.find({'titulo': {	'$exists': False},'imdb': {'$not': {'$regex': '.* .*'}}}).limit(20):
		#print(r)
		try:
			im = str(r['imdb']).strip()[2:]
			imdb = IMDb()
			print(int(im))
			movie = imdb.get_movie(int(im))
			movie.fetch()
			print(movie.__dict__['title'])
			print(movie.__dict__['year'])
			db.registros.update_one({"_id": r['_id']}, {"$set": {"titulo": movie.__dict__['title'],"ano": movie.__dict__['year']}})
			print('Sem Título: ', im, movie.__dict__['title'])
			repetir = True
		except:
			db.registros.update_one({"_id": r['_id']}, {"$set": {"titulo": 'Título não encontrado',"ano": 0}})
			repetir = True
			print('Erro Sem Título: ', im)

	if repetir:
		corrigir_titulo_filme()


def corrigir_titulo_serie():
	print('corrigir_titulo_serie Iniciado')
	repetir = False
	for r in db.registros.find({'titulo': {'$exists': False},'imdb': {'$regex': '.* .*'}}).limit(1):
		#print(r)
		try:
			im = str(r['imdb']).strip()[2:r['imdb'].index(" ")]
			imdb = IMDb()
			print(int(im))
			movie = imdb.get_movie(int(im))
			movie.fetch()
			print(movie.__dict__['title'])
			print(movie.__dict__['year'])
			print('.*' + str(im) + '.*')
			db.registros.update_many({'imdb': {'$regex': '.*' + str(im) + '.*'}}, {"$set": {"titulo": movie.__dict__['title'],"ano": movie.__dict__['year']}})
			print('Sem Título: ', im, movie.__dict__['title'])
			repetir = True
		except:
			im = str(r['imdb']).strip()[2:r['imdb'].index(" ")]
			db.registros.update_many({'imdb': {'$regex': '.*' + str(im) + '.*'}}, {"$set": {"titulo": 'Título não encontrado',"ano": 0}})
			repetir = True
			print('Erro Sem Título: ', im)

	if repetir:
		corrigir_titulo_serie()


@app.route('/link')
def link():
	q = request.args.get("q")
	i = request.args.get("i")
	print(q)
	if (q != None):
		socketio.start_background_task(thread_link, q, i)
	return redirect("/", code=302)


@app.route('/')
def hello_world():
	q = request.args.get("q")
	print(q)
	if (q != None):
		lin = "https://ondeeubaixo.net/index.php?campo1=" + q + "&nome_campo1=pesquisa&categoria=lista&"
		socketio.start_background_task(thread_lista, lin, 3)
	return render_template('busca.html')




def thread_link(q, im):

	l = q
	id_imdb = im
	print(q)
	socketio.emit('atualizar', 'Carregando: ' + l)
	r2 = session.get(l)
	try:
		id_imdb = r2.html.find("a[href*='www.imdb.com']", first=True).attrs['href']
		id_imdb = id_imdb.replace("http://www.imdb.com/title/", "").replace("https://www.imdb.com/title/", "").replace("/", "").replace("/", "").replace("?ref_=nv_sr_", "").replace("?ref_=plg_rt_1", "").replace("http:www.imdb.com","").strip()
	except:
		print('Erro IMDB')

	s = []
	socketio.emit('atualizar', 'IMDB:' + id_imdb)
	for html in r2.html.find('a[href^="magnet"]'):
		s.append({'imdb': id_imdb, 'link': list(html.links)[0]})
	for html in r2.html.find('a[href^="http://www.meucarrao.info/magnet/?xt"]'):
		s.append({'imdb': id_imdb, 'link': list(html.links)[0]})
	carregar_sky_forcar(s,True)

def thread_lista(url, tamanho):
	s = []
	global continuar
	for x in range(1, tamanho):
		print(url + str(x))
		if continuar:
			r = session.get(url + str(x))
			titulos = r.html.find('.list-inline > li')
			for elem in titulos:
				if continuar:
					# print(elem.find('a',first=True).attrs)
					link = elem.find('a', first=True).attrs['href']
					dublado = elem.find('.idioma_lista', first=True).text.strip()
					# print(link, dublado)
					if dublado == "Dublado":
						print(link)
						socketio.emit('atualizar', 'Link: ' + link)
						r2 = session.get(link)
						id_imdb = ""
						try:
							id_imdb = r2.html.find("a[href*='www.imdb.com']", first=True).attrs['href']
							id_imdb = id_imdb.replace("http://www.imdb.com/title/", "").replace("https://www.imdb.com/title/", "").replace("/", "").replace("/", "").replace("?ref_=nv_sr_", "").replace("?ref_=plg_rt_1", "").replace("http:www.imdb.com", "").strip()
						except:
							id_imdb = ""

						for html in r2.html.find('a[href^="magnet"]'):
							s.append({'imdb': id_imdb, 'link': list(html.links)[0]})
							#db.magnets.insert_one({'imdb': id_imdb, 'link': list(html.links)[0]})
	carregar_sky(s)

def thread_busca(url, tamanho):
	s = []
	global continuar
	for x in range(1, tamanho):
		print(url + str(x))
		if continuar:
			r = session.get(url + str(x))
			titulos = r.html.find('.list-inline .semelhantes')
			for elem in titulos:
				if continuar:
					# print(elem.find('a',first=True).attrs)
					link = elem.find('a', first=True).attrs['href']
					print(link)
					socketio.emit('atualizar', 'Link: ' + link)
					r2 = session.get(link)
					id_imdb = ""
					try:
						id_imdb = r2.html.find("a[href*='www.imdb.com']", first=True).attrs['href']
						id_imdb = id_imdb.replace("http://www.imdb.com/title/", "").replace("https://www.imdb.com/title/", "").replace("/", "").replace("/", "").replace("?ref_=nv_sr_", "").replace("?ref_=plg_rt_1", "").replace("http:www.imdb.com", "").strip()
					except:
						id_imdb = ""

					for html in r2.html.find('a[href^="magnet"]'):
						s.append({'imdb': id_imdb, 'link': list(html.links)[0]})
						#db.magnets.insert_one({'imdb': id_imdb, 'link': list(html.links)[0]})
	carregar_sky(s)


def thread_lista_preferidos():
	s = []
	global continuar
	for pref in db.preferidos.find({}):
		if continuar:
			r = session.get("https://ondeeubaixo.net/index.php?campo1=" + pref["nome"] + "&nome_campo1=pesquisa&categoria=lista&")
			titulos = r.html.find('.list-inline .semelhantes')
			for elem in titulos:
				# print(elem.find('a',first=True).attrs)
				link = elem.find('a', first=True).attrs['href']

				r2 = session.get(link)
				id_imdb = ""
				try:
					id_imdb = r2.html.find("a[href*='www.imdb.com']", first=True).attrs['href']
					id_imdb = id_imdb.replace("http://www.imdb.com/title/", "").replace("https://www.imdb.com/title/", "").replace("/", "").replace("/", "").replace("?ref_=nv_sr_", "").replace("?ref_=plg_rt_1", "").replace("http:www.imdb.com", "").strip()
				except:
					id_imdb = ""

				if id_imdb == pref["imdb"]:
					print(link)
					socketio.emit('atualizar', 'Link: ' + link)
					for html in r2.html.find('a[href^="magnet"]'):
						s.append({'imdb': id_imdb, 'link': list(html.links)[0]})
					
	carregar_sky(s)


@socketio.on('preferido')
def preferido(im, nome):
	print("Preferido:" + im)
	print(db.preferidos.find({'imdb': im}).count())
	if db.preferidos.find({'imdb': im}).count() == 0:
		db.preferidos.insert_one({
			'imdb': im,
			'nome': nome
		})
	socketio.emit('resposta_funcoes', 'Adicionado ao Preferidos: ' + nome)


@socketio.on('remove_preferido')
def remove_preferido(im):
	print("Não Preferido:" + im)
	db.preferidos.delete_many({
		'imdb': im
	})
	socketio.emit('resposta_funcoes', 'Removido dos Preferidos: ' + im)


@socketio.on('apagar')
def apagar(im):
	print("Apagado: " + im)
	db.registros.delete_many({'imdb': {'$regex': '.*' + im}})
	socketio.emit('resposta_funcoes', 'Apagado: ' + im)


@socketio.on('carregar_lancamentos')
def sock_lancamento():    
    nav = sock_navegar()
    seq = 1
    for n in nav:
        im_n = n['link'][7:16]
        for b in db.registros.find({"$or":[{'imdb': {'$regex': '.*'+im_n+'.*','$options': 'i'}}]}).sort('imdb',-1).limit(1):
	        socketio.emit('atualizar', dumps(b))    
        seq = seq + 1
    
def sock_navegar():
    s = []    
    r = session.get('https://www.imdb.com/chart/moviemeter?sort=us,desc&mode=simple&page=1')
    titulos = r.html.find('.lister-list tr .titleColumn')
    for elem in titulos:
        link = elem.find('a', first=True).attrs['href']
        ano = elem.find('span', first=True).text
        titulo =  elem.find('a', first=True).text.strip()
        s.append({'link':link, 'ano':ano, 'titulo':titulo+' (Filme)'})        
    
    r = session.get('https://www.imdb.com/chart/tvmeter?sort=us,desc&mode=simple&page=1')
    titulos = r.html.find('.lister-list tr .titleColumn')
    for elem in titulos:
        link = elem.find('a', first=True).attrs['href']
        ano = elem.find('span', first=True).text
        titulo =  elem.find('a', first=True).text.strip()
        s.append({'link':link, 'ano':ano, 'titulo':titulo+' (Série)'})        
    
    return s

@socketio.on('link')
def sock_link(message, im):
	socketio.emit('limpar')
	global continuar
	continuar = True
	socketio.start_background_task(thread_link, message, im)

@socketio.on('buscar')
def sock_buscar(message):
	socketio.emit('limpar')
	socketio.emit('atualizar', 'Buscando: ' + message)
	global continuar
	continuar = True
	lin = "https://ondeeubaixo.net/index.php?campo1=" + message + "&nome_campo1=pesquisa&categoria=lista&"
	socketio.start_background_task(thread_busca, lin, 3)


@socketio.on('lista')
def sock_lista(message):
	socketio.emit('limpar')
	socketio.emit('atualizar', 'Buscando: ')
	global continuar
	continuar = True
	socketio.start_background_task(thread_lista, message, 3)

@socketio.on('lista_preferidos')
def sock_lista_preferidos():
	socketio.emit('limpar')
	socketio.emit('atualizar', 'Buscando: ')
	global continuar
	continuar = True
	socketio.start_background_task(thread_lista_preferidos)

@socketio.on('inicio')
def sock_iniciado():
	print('inicio')
	#socketio.start_background_task(thread_lista, 'https://ondeeubaixo.net/lancamentos-', 3)

@socketio.on('parar')
def parar():
	print("Parando")
	global continuar
	continuar = False

@socketio.on('carregar_preferidos')
def sock_preferidos():
	global continuar
	continuar = True
	socketio.emit('limpar')
	socketio.emit('atualizar', 'Buscando: ')
	#socketio.emit('resposta_preferidos', dumps(db.preferidos.find()))
	for b in db.preferidos.find().sort('imdb',-1):
		socketio.emit('atualizar', dumps(b))
	socketio.emit('atualizar', 'Fim da Busca')

@socketio.on('buscar_im')
def buscar_im(nome):	
	socketio.emit('limpar')
	socketio.emit('atualizar', 'Buscando: '+nome)
	print("Buscando IMDB: " + nome)
	for b in db.registros.find({"$or":[{'nome': {'$regex': '.*'+nome+'.*','$options': 'i'}},{'titulo': {'$regex': '.*'+nome+'.*','$options': 'i'}},{'imdb': {'$regex': '.*'+nome+'.*','$options': 'i'}}]}).sort('imdb',-1):
		socketio.emit('atualizar', dumps(b))
	socketio.emit('atualizar', 'Fim da Busca')

@socketio.on('connect')
def test_connect():
	print('conectado')

@socketio.on('tabela')
def sock_tabela():
	global continuar
	continuar = True
	socketio.emit('carregar_tabela', dumps(db.registros.find({})))

if __name__ == "__main__":
	port = int(os.environ.get("PORT", 3000))
	socketio.run(app,  debug=False,  host='0.0.0.0', port=port)





