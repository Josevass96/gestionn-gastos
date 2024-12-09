from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Cargar las credenciales desde el archivo JSON
cred = credentials.Certificate('gestion-de-gastos-434fb-firebase-adminsdk-9goqw-9d605c56ff.json')  # Asegúrate de que el archivo exista
firebase_admin.initialize_app(cred)

# Crear un cliente Firestore
db_firestore = firestore.client()

app = Flask(__name__)
CORS(app)

# Crear departamentos
@app.route('/crear_departamentos', methods=['POST'])
def crear_departamentos():
    departamentos = [
        {
            'CodDepto': 'A101', 'Piso': '1', 'Numero': '01', 'Arrendado': False,
            'RutProp': '11111111-1', 'Estado': 'Disponible', 'RutArre': None,
            'FechaIniC': None, 'FechaFinC': None, 'Observacion': None, 'NumHab': 3, 'NumBaños': 2
        },
        {
            'CodDepto': 'A102', 'Piso': '1', 'Numero': '02', 'Arrendado': False,
            'RutProp': '22222222-2', 'Estado': 'Disponible', 'RutArre': None,
            'FechaIniC': None, 'FechaFinC': None, 'Observacion': None, 'NumHab': 2, 'NumBaños': 1
        },
        # Agrega más departamentos según sea necesario
    ]

    batch = db_firestore.batch()
    for depto in departamentos:
        ref = db_firestore.collection('departamentos').document(depto['CodDepto'])
        batch.set(ref, depto)
    batch.commit()

    return jsonify({'mensaje': 'Departamentos creados exitosamente'}), 201

# Listar departamentos
@app.route('/listar_departamentos', methods=['GET'])
def listar_departamentos():
    departamentos_ref = db_firestore.collection('departamentos')
    departamentos = departamentos_ref.stream()

    lista_departamentos = []
    for doc in departamentos:
        lista_departamentos.append(doc.to_dict())

    if not lista_departamentos:
        return jsonify({'mensaje': 'No hay departamentos registrados'}), 200

    return jsonify({'departamentos': lista_departamentos}), 200

# Crear gastos comunes
@app.route('/crear_gastos_comunes', methods=['POST'])
def crear_gastos_comunes():
    data = request.get_json()
    mes = data.get('mes')  # Puede ser None
    anio = data.get('anio')

    if not anio:
        return jsonify({'error': 'El año es obligatorio'}), 400

    departamentos_ref = db_firestore.collection('departamentos')
    departamentos = departamentos_ref.stream()

    batch = db_firestore.batch()
    for departamento in departamentos:
        depto_data = departamento.to_dict()
        cod_depto = depto_data['CodDepto']

        if mes:
            gasto = {
                'mes': mes,
                'anio': anio,
                'valor_pagado': 0.0,
                'fecha_pago': None,
                'atrasado': False,
                'cod_depto': cod_depto
            }
            ref = db_firestore.collection('gastos_comunes').document(f'{cod_depto}_{anio}_{mes}')
            batch.set(ref, gasto)
        else:
            for mes in range(1, 13):  # Crear para todos los meses
                gasto = {
                    'mes': mes,
                    'anio': anio,
                    'valor_pagado': 0.0,
                    'fecha_pago': None,
                    'atrasado': False,
                    'cod_depto': cod_depto
                }
                ref = db_firestore.collection('gastos_comunes').document(f'{cod_depto}_{anio}_{mes}')
                batch.set(ref, gasto)

    batch.commit()

    return jsonify({'mensaje': 'Gastos comunes creados exitosamente'}), 201

# Listar gastos comunes
@app.route('/gastos_comunes', methods=['GET'])
def obtener_gastos_comunes():
    gastos_ref = db_firestore.collection('gastos_comunes')
    gastos = gastos_ref.stream()

    lista_gastos = []
    for doc in gastos:
        lista_gastos.append(doc.to_dict())

    return jsonify(lista_gastos), 200

# Marcar gasto como pagado
@app.route('/marcar_como_pagado', methods=['POST'])
def marcar_como_pagado():
    data = request.get_json()

    if 'CodDepto' not in data or 'mes' not in data or 'anio' not in data or 'fecha_pago' not in data:
        return jsonify({'error': 'Campos CodDepto, mes, anio, y fecha_pago son requeridos'}), 400

    cod_depto = data['CodDepto']
    mes = data['mes']
    anio = data['anio']
    fecha_pago = data['fecha_pago']

    ref = db_firestore.collection('gastos_comunes').document(f'{cod_depto}_{anio}_{mes}')
    doc = ref.get()

    if not doc.exists:
        return jsonify({'error': 'Gasto común no encontrado'}), 404

    gasto = doc.to_dict()

    if gasto['fecha_pago']:
        return jsonify({'error': 'Pago duplicado: este gasto ya fue pagado anteriormente'}), 409

    fecha_vencimiento = datetime(int(anio), int(mes), 15)  # Suponiendo que la fecha límite es el 15 del mes
    fecha_pago_dt = datetime.strptime(fecha_pago, '%Y-%m-%d')
    atrasado = fecha_pago_dt > fecha_vencimiento

    ref.update({
        'fecha_pago': fecha_pago,
        'atrasado': atrasado
    })

    return jsonify({'mensaje': 'Gasto común marcado como pagado', 'atrasado': atrasado}), 200

# Listar gastos pendientes
@app.route('/listar_gastos_pendientes', methods=['POST'])
def listar_gastos_pendientes():
    data = request.get_json()

    if 'mes' not in data or 'anio' not in data:
        return jsonify({'error': 'Se requiere mes y año como parámetros en el cuerpo de la solicitud'}), 400

    mes = data['mes']
    anio = data['anio']

    gastos_ref = db_firestore.collection('gastos_comunes')
    query = gastos_ref.where('anio', '==', anio).where('mes', '<=', mes).where('fecha_pago', '==', None)
    gastos_pendientes = query.stream()

    lista_gastos = []
    for doc in gastos_pendientes:
        lista_gastos.append(doc.to_dict())

    if not lista_gastos:
        return jsonify({'mensaje': 'Sin montos pendientes'}), 200

    return jsonify({'gastos_pendientes': lista_gastos}), 200

if __name__ == '__main__':
    app.run(debug=True)
