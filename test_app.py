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

    def test_exportar_comandas(self):
        import openpyxl
        import io

        # 1. Add comanda and close it (verde)
        self.app.post('/adicionar', data=dict(nome='Fechada', telefone='1', numero_comanda='200', qtd_pessoas='1'))
        self.app.post('/fechar/1', follow_redirects=True)

        # 2. Add comanda, launch couvert, and leave open (amarelo)
        self.app.post('/adicionar', data=dict(nome='Com Couvert', telefone='2', numero_comanda='201', qtd_pessoas='1'))
        self.app.post('/lancar_couvert/2', follow_redirects=True)

        # 3. Add comanda, leave open, no couvert (branco)
        self.app.post('/adicionar', data=dict(nome='Aberta Sem Couvert', telefone='3', numero_comanda='202', qtd_pessoas='1'))

        # Exportar
        rv = self.app.get('/exportar')
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # Load excel file
        excel_data = io.BytesIO(rv.data)
        wb = openpyxl.load_workbook(excel_data)
        ws = wb.active

        self.assertEqual(ws.title, "Comandas")

        # Check rows (row 1 is header)
        rows = list(ws.iter_rows())
        self.assertTrue(len(rows) >= 4) # 1 header + 3 comandas

        # Verifying row colors
        # Row 2 (ID 1, Fechada -> Verde)
        self.assertEqual(rows[1][0].fill.start_color.index, '0000FF00')

        # Row 3 (ID 2, Open with Couvert -> Amarelo)
        self.assertEqual(rows[2][0].fill.start_color.index, '00FFFF00')

        # Row 4 (ID 3, Open without Couvert -> Branco)
        self.assertEqual(rows[3][0].fill.start_color.index, '00FFFFFF')


if __name__ == '__main__':
    unittest.main()
