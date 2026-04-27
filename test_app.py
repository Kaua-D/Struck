import unittest
import sqlite3
import os
from app import app, init_db

import app as application

class RestauranteTestCase(unittest.TestCase):
    def setUp(self):
        # Set a test database name
        self.test_db = "test_restaurante.db"
        application.DB_NAME = self.test_db
        
        # Initialize DB
        with app.app_context():
            init_db()
            
        self.app = app.test_client()

    def tearDown(self):
        # Remove the test database
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_adicionar_comanda(self):
        rv = self.app.post('/adicionar', data=dict(
            nome='Teste User',
            telefone='123456789',
            numero_comanda='100',
            qtd_pessoas='2'
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Teste User', rv.data)
        self.assertIn(b'100', rv.data)

    def test_adicionar_comanda_duplicada(self):
        # Adicionar primeira comanda
        self.app.post('/adicionar', data=dict(
            nome='Cliente 1',
            telefone='111',
            numero_comanda='500',
            qtd_pessoas='2'
        ), follow_redirects=True)
        
        # Tentar adicionar segunda com o mesmo número
        rv = self.app.post('/adicionar', data=dict(
            nome='Cliente 2',
            telefone='222',
            numero_comanda='500', # Duplicado
            qtd_pessoas='3'
        ), follow_redirects=True)
        
        self.assertEqual(rv.status_code, 200)
        # Deve conter mensagem de erro
        self.assertIn(b'Erro: A comanda 500 j', rv.data)

    def test_lancar_couvert(self):
        # Add comanda first
        self.app.post('/adicionar', data=dict(
            nome='Teste Couvert',
            telefone='987654321',
            numero_comanda='101',
            qtd_pessoas='4'
        ), follow_redirects=True)
        
        # Check it is in "Aguardando Couvert" (implied by not having "Couvert OK")
        rv = self.app.get('/')
        self.assertIn(b'Teste Couvert', rv.data)
        
        # Launch Couvert (ID=1)
        rv = self.app.post('/lancar_couvert/1', follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Couvert Lan\xc3\xa7ado', rv.data)

    def test_fechar_comanda(self):
         # Add comanda first
        self.app.post('/adicionar', data=dict(
            nome='Teste Fechar',
            telefone='55555555',
            numero_comanda='102',
            qtd_pessoas='1'
        ), follow_redirects=True)
        
        # Close it (ID=1)
        rv = self.app.post('/fechar/1', follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        
        # Should not be visible anymore
        self.assertNotIn(b'Teste Fechar', rv.data)

    def test_busca_comanda(self):
        # Adicionar algumas comandas
        self.app.post('/adicionar', data=dict(nome='A', telefone='1', numero_comanda='10', qtd_pessoas='1'))
        self.app.post('/adicionar', data=dict(nome='B', telefone='2', numero_comanda='20', qtd_pessoas='1'))
        
        # Buscar pela comanda 10
        rv = self.app.get('/?busca=10')
        self.assertIn(b'Comanda: 10', rv.data)
        self.assertNotIn(b'Comanda: 20', rv.data) 
        
        # Buscar pela comanda 20
        rv = self.app.get('/?busca=20')
        self.assertIn(b'Comanda: 20', rv.data)
        self.assertNotIn(b'Comanda: 10', rv.data)

    def test_exportar_xml(self):
        # Comanda aberta sem couvert
        self.app.post('/adicionar', data=dict(
            nome='Aberto Sem Couvert', telefone='1', numero_comanda='1001', qtd_pessoas='1'
        ), follow_redirects=True)

        # Comanda aberta com couvert (lançar couvert para ID=2, assumindo IDs sequenciais)
        self.app.post('/adicionar', data=dict(
            nome='Aberto Com Couvert', telefone='2', numero_comanda='1002', qtd_pessoas='1'
        ), follow_redirects=True)
        self.app.post('/lancar_couvert/2', follow_redirects=True)

        # Comanda fechada
        self.app.post('/adicionar', data=dict(
            nome='Fechada', telefone='3', numero_comanda='1003', qtd_pessoas='1'
        ), follow_redirects=True)
        self.app.post('/fechar/3', follow_redirects=True)

        rv = self.app.get('/exportar_xml')
        self.assertEqual(rv.status_code, 200)
        self.assertTrue(rv.content_type.startswith('application/xml'))

        xml_data = rv.data.decode('utf-8')
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_data)

        comandas = root.findall('comanda')
        self.assertEqual(len(comandas), 3)

        # Verificando as cores de cada comanda
        cores = []
        for comanda in comandas:
            cor_elem = comanda.find('cor')
            if cor_elem is not None:
                cores.append(cor_elem.text)
            else:
                cores.append(None)

        # O 1001 deve ser None (sem tag cor de acordo com a logica original se nao preencher)
        # 1002 deve ser amarelo
        # 1003 deve ser verde
        self.assertEqual(cores[0], None)
        self.assertEqual(cores[1], "amarelo")
        self.assertEqual(cores[2], "verde")

if __name__ == '__main__':
    unittest.main()
