# Proyecto Flask: proyección poblacional con 4 datos y 3 tipos de proyección


import pandas as pd
import numpy as np
from scipy.stats import gmean
from flask import Flask, render_template, request, session, redirect, url_for
import math
import os
import logging
import pprint



app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "322ss11aAZ2S2sss")
"""

# NOTAS DE APRENDIZAJE

1. Flask siempre recibe los datos como strings, por lo que es necesario convertirlos al tipo adecuado (int, float, etc.) antes de usarlos en cálculos.
2. Es preferible poner session["datos"] = datos al final de cada POST, después de haber procesado y validado todos los datos.
3. para evitar problemas los botones de POST deben estar dentro del <form> y no fuera.
4. Los comentarios en HTML son <!-- comentario -->, mientras que en Jinja2 son {# comentario #}. Si comentas con HTML dentro de un bloque Jinja2, puede causar errores.
5. El filtro tojson de jinja 2 covierte todos los diccionarios a formato json, las claves en Json siempre son string.
6. nonlocal sirve para modificar variables de una función externa.
"""

# 0. FUNCIONES BÁSICAS
def to_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0

def to_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


# Paso 1: DATOS GENERALES
@app.route("/", methods=["GET", "POST"])
def paso1():
    error = None
    datos = session.get('datos', {
        'nombre_proyecto': 'Colegio XYZ',
        'nombre_colegio': 'Mejoramiento y Ampliación del Colegio XYZ',
        'distrito': 'CHAcla',
        'nivel': 'Secundaria',
        'radio_influencia': 3,
        'area_distrito': 77.72,
        'est_by_aula': 30,
        'anio_form': 2024,
        'cantidad_anios_matricula': 5,
        'anio_i': 2027,
        'anio_f': 2036,
        "anio_censo1": 2007,
        "anio_censo2": 2017,
        "turnos": 2,
    })

    # Diccionarios por defecto
    pop_censo1_default = 478278
    pop_censo2_default = 624172
    dic_mat_by_anio_default = {
        2019: {12: 163, 13: 119, 14: 120, 15: 97, 16: 99},
        2020: {12: 173, 13: 146, 14: 103, 15: 112, 16: 89},
        2021: {12: 170, 13: 168, 14: 142, 15: 102, 16: 113},
        2022: {12: 170, 13: 161, 14: 157, 15: 135, 16: 96},
        2023: {12: 164, 13: 166, 14: 138, 15: 138, 16: 127}
    }
    dic_pop_edad_default = {  
                            2007: {12: 9153, 13: 8881, 14: 9217, 15: 9539, 16: 8739},
                            2017: {12: 10292, 13: 10292, 14: 9615, 15: 9385, 16: 9558}
    }
    dic_no_promv_default = {  
                            2019: {12: 23, 13: 19, 14: 8, 15: 10, 16: 6},      
                            2020: {12: 0, 13: 1, 14: 0, 15: 1, 16: 19},        
                            2021: {12: 1, 13: 1, 14: 2, 15: 0, 16: 0},
                            2022: {12: 3, 13: 5, 14: 8, 15: 3, 16: 1},
                            2023: {12: 8, 13: 18, 14: 11, 15: 8, 16: 11}
    }

    default_dicts = {
        "pob_censo1": pop_censo1_default,
        "pob_censo2": pop_censo2_default,
        "dic_mat_by_anio": dic_mat_by_anio_default,
        "dic_pop_edad": dic_pop_edad_default,
        "dic_no_promv": dic_no_promv_default
    }

    # Asignar valores por defecto solo si faltan
    asignado_defecto = False
    for key, default_value in default_dicts.items():
        if key not in datos or not datos.get(key):
            datos[key] = default_value
            asignado_defecto = True
    if asignado_defecto:
        session["datos"] = datos

    if request.method == 'POST':
        # Actualizar datos con lo enviado por el usuario
        for campo in datos.keys():
            if campo in request.form:
                datos[campo] = request.form.get(campo, "")

        # Edades según nivel
        datos["edades"] = list(range(6, 12)) if datos.get("nivel") == "Primaria" else list(range(12, 17))

        # Validaciones y conversiones
        def validar_rango(valor, tipo, minv, maxv, defecto, mensaje):
            v = tipo(valor)  # Convierte el valor al tipo deseado (int, float, etc.)
            if not (minv <= v <= maxv):  # Verifica si está dentro del rango permitido
                nonlocal error          # Permite modificar la variable 'error' de la función externa
                error = mensaje         # Asigna el mensaje de error si el valor no es válido
                return defecto          # Devuelve el valor por defecto si está fuera de rango
            return v                    # Si está bien, devuelve el valor convertido

        datos["radio_influencia"] = validar_rango(datos["radio_influencia"], to_float, 0.97, 117, 3, "El radio de influencia debe estar entre 0.97 y 117 km.")
        datos["area_distrito"] = validar_rango(datos["area_distrito"], to_float, 3, 42298, 77.7, "El área del distrito debe estar entre 3 y 42298 km².")
        datos["est_by_aula"] = validar_rango(datos["est_by_aula"], to_float, 5, 50, 30, "El número de estudiantes por aula debe estar entre 5 y 50.")
        datos["anio_form"] = validar_rango(datos["anio_form"], to_int, 2017, 2035, 2024, "El año de formulación debe estar entre 2017 y 2035.")
        datos["cantidad_anios_matricula"] = validar_rango(datos["cantidad_anios_matricula"], to_int, 1, 10, 5, "La cantidad de años de matrícula debe estar entre 1 y 10.")
        datos["anio_i"] = to_int(datos["anio_i"])
        datos["anio_f"] = to_int(datos["anio_f"])
        if not (datos["anio_form"] < datos["anio_i"] < datos["anio_f"]):
            error = "El año de inicio de operaciones debe ser mayor al año de formulación y menor al año final."
            datos["anio_i"] = datos["anio_form"] + 3 if datos["anio_form"] + 3 < datos["anio_f"] else datos["anio_form"] + 1
        if not (datos["anio_form"] < datos["anio_f"]):
            error = "El año final debe ser mayor al año de formulación."
            datos["anio_f"] = datos["anio_i"] + 9
        datos["anio_censo1"] = validar_rango(datos["anio_censo1"], to_int, 2007, 2100, 2007, "El primer año de censo debe ser mayor o igual a 2007.")
        datos["anio_censo2"] = validar_rango(datos["anio_censo2"], to_int, 2017, 2100, 2017, "El segundo año de censo debe ser mayor o igual a 2017.")
        datos["turnos"] = validar_rango(datos["turnos"], to_int, 1, 4, 2, "La cantidad de turnos debe estar entre 1 y 4.")

        # Variables derivadas
        anios_hist = list(range(datos["anio_form"] - datos["cantidad_anios_matricula"], datos["anio_form"]))
        datos["anios_total"] = list(range(datos["anio_form"] - datos["cantidad_anios_matricula"], datos["anio_f"] + 1))
        datos["anios_hist"] = [to_int(anio) for anio in anios_hist]
        datos["anios_proyec"] = list(range(datos["anio_form"], datos["anio_f"] + 1))
        datos["anios_proyec_0"] = list(range(datos["anio_form"], datos["anio_i"]))
        datos["anios_proyec_f"] = list(range(datos["anio_i"], datos["anio_f"] + 1))

        if error:
            return render_template("paso1.html", datos=datos, error=error)
        else:
            session["datos"] = datos

    logging.warning("Datos en paso1:\n" + pprint.pformat(datos, indent=3))
    return render_template("paso1.html", datos=datos, error=error)

# Paso 2: Población, matrícula y no promovidos
@app.route("/paso2", methods=["GET", "POST"])
def paso2():
    error = None
    datos = session.get('datos', {})
    # Convertir a int los valores de diccionarios si es que vienen como strings
    if isinstance(datos.get("dic_pop_edad"), dict):
        datos["dic_pop_edad"] = {to_int(anio): {to_int(edad): to_int(cant) for edad, cant in edades.items()} for anio, edades in datos["dic_pop_edad"].items()}    
    if isinstance(datos.get("dic_mat_by_anio"), dict):
        datos["dic_mat_by_anio"] = {to_int(anio): {to_int(edad): to_int(cant) for edad, cant in edades.items()} for anio, edades in datos["dic_mat_by_anio"].items()}
    if isinstance(datos.get("dic_no_promv"), dict):
        datos["dic_no_promv"] = {to_int(anio): {to_int(edad): to_int(cant) for edad, cant in edades.items()} for anio, edades in datos["dic_no_promv"].items()}

    if request.method == 'POST':
        # ---------------------------------------------------
        # POST para guardar población total del distrito
        valor = request.form.get("pob_censo1")
        valor_int = to_int(valor)
        if valor_int <= 0:
            error = "Los valores de población total deben ser positivos. Corrige los datos."
        datos["pob_censo1"] = valor_int
        
        valor = request.form.get("pob_censo2")
        valor_int = to_int(valor)
        if valor_int <= 0:
            error = "Los valores de población deben ser positivos."
        datos["pob_censo2"] = valor_int
        # ---------------------------------------------------
        # POST para guardar población por edades del distrito
        dic_pop_edad = {}            
        for anio in [datos['anio_censo1'], datos['anio_censo2']]:
            dic_pop_edad[int(anio)] = {}
            for edad in datos.get("edades", []):
                valor = request.form.get(f'pop_edad_{anio}_{edad}', 0) or 0
                valor_int = to_int(valor)
                if valor_int < 0:
                    error = "No se permiten valores negativos en población por edades. Corrige los datos."
                dic_pop_edad[int(anio)][int(edad)] = valor_int
        datos["dic_pop_edad"] = dic_pop_edad
        # ---------------------------------------------------
        # POST para guardar datos de matrícula
        dic_matricula = {}
        for anio in datos.get("anios_hist", []):
            dic_matricula[int(anio)] = {}
            for edad in datos.get("edades", []):
                valor = request.form.get(f'matricula_{anio}_{edad}', 0) or 0
                valor_int = to_int(valor)
                if valor_int < 0:
                    error = "No se permiten valores negativos en matrícula. Corrige los datos."
                dic_matricula[int(anio)][int(edad)] = valor_int
        datos["dic_mat_by_anio"] = dic_matricula
        # ---------------------------------------------------
        # POST para guardar datos de no promovidos
        dic_no_promv = {}
        for anio in datos.get("anios_hist", []):
            dic_no_promv[int(anio)] = {}
            for edad in datos.get("edades", []):
                valor = request.form.get(f'noprom_{anio}_{edad}', 0) or 0
                valor_int = to_int(valor)
                if valor_int < 0:
                    error = "No se permiten valores negativos en no promovidos. Corrige los datos."
                dic_no_promv[int(anio)][int(edad)] = valor_int
        datos["dic_no_promv"] = dic_no_promv
        
        # Si hubo error, NO guardar en sesión y mostrar el mensaje
        if error:
            return render_template(
                "paso2.html",
                datos=datos,
                error=error
            )
        else:
            session["datos"] = datos        

    # Mostrar datos
    logging.warning("Datos en paso2:\n" + pprint.pformat(datos, indent=3)) # Es loging.warning para que se vea en la consola de Heroku. Si se pone después del return no se ve, porque no se ejecuta.
    return render_template(
        "paso2.html",
        datos=datos,
        error=error
    )
# Paso 3: Proyección y gráfico
@app.route("/paso3", methods=["GET", "POST"])
def paso3():
    # ##################################
    # RECUPERAR DATOS DE SESIÓN
    # ##################################    
    datos = session.get("datos", {})
    resultados = session.get("resultados", {})
    # Convertir a int los valores de diccionarios si es que vienen como strings
    if isinstance(datos.get("dic_pop_edad"), dict):
        datos["dic_pop_edad"] = {to_int(anio): {to_int(edad): to_int(cant) for edad, cant in edades.items()} for anio, edades in datos["dic_pop_edad"].items()}    
    if isinstance(datos.get("dic_mat_by_anio"), dict):
        datos["dic_mat_by_anio"] = {to_int(anio): {to_int(edad): to_int(cant) for edad, cant in edades.items()} for anio, edades in datos["dic_mat_by_anio"].items()}
    if isinstance(datos.get("dic_no_promv"), dict):
        datos["dic_no_promv"] = {to_int(anio): {to_int(edad): to_int(cant) for edad, cant in edades.items()} for anio, edades in datos["dic_no_promv"].items()}    
    
    # ##################################
    # VARIABLES Y PARÁMETROS
    # ##################################    
    pob_censo1 = datos.get("pob_censo1", 0) or 0
    pob_censo2 = datos.get("pob_censo2", 0) or 0
    anio_censo1 = datos.get("anio_censo1", 2007)
    anio_censo2 = datos.get("anio_censo2", 2017)
    anios_hist = datos.get("anios_hist", [])
    anios_proy = datos.get("anios_proyec", [])
    anios_total = datos.get("anios_total", [])
    r = datos.get("radio_influencia", 3)
    area = datos.get("area_distrito", 77.7) or 1  # Evitar división por cero
    edades = datos.get("edades", [])
    dic_pop_edad = datos.get("dic_pop_edad", {})
    dic_mat_by_anio = datos.get("dic_mat_by_anio", {})
    dic_no_promv = datos.get("dic_no_promv", {})
    est_by_aula = datos.get("est_by_aula", 30)
    turnos = datos.get("turnos", 2)
    nombre_colegio = datos.get("nombre_colegio", "INSERTAR NOMBRE DEL COLEGIO")
    nombre_proyecto = datos.get("nombre_proyecto", "INSERTAR NOMBRE DEL PROYECTO")
    # ##################################
    # CÁLCULO DE LA POBLACIÓN TOTAL
    # ##################################
    # Población de todo el distrito
    dic_pop_total = {}
    if pob_censo1 > 0 and pob_censo2 > 0:
        tasa_poptotal = (pob_censo2 / pob_censo1) ** (1 / (anio_censo2 - anio_censo1)) - 1
        # Se tasas negativas simpre se ponen en 0
        if tasa_poptotal < 0:
            tasa_poptotal = 0
    else:
        tasa_poptotal = 0
        
    resultados["tasa_poptotal"] = tasa_poptotal
    for anio in anios_total:
        if pob_censo2:
            dic_pop_total[anio] = int(pob_censo2 * (1 + tasa_poptotal) ** (anio - anio_censo2))
        elif pob_censo1:
            dic_pop_total[anio] = int(pob_censo1 * (1 + tasa_poptotal) ** (anio - anio_censo1))
        else:
            dic_pop_total[anio] = 0
    resultados["tasa_poptotal"] = tasa_poptotal
    resultados["dic_pop_total"] = dic_pop_total
    ###################################
    # CÁLCULO DE LA POBLACIÓN REFERENCIAL
    ###################################
    # Población del área de infuencia de todas las edades
    dic_pop_ref = {}    
    for anio in anios_proy:
        dic_pop_ref[anio] = int((math.pi * (r ** 2) / area) * dic_pop_total[anio])
    resultados["dic_pop_ref"] = dic_pop_ref

    ###################################
    # CÁLCULO DE LA POBLACIÓN POTENCIAL
    ###################################
    # Población que vive en el área de influencia y del grupo etario normativo
    tasa_by_edad = {}
    for edad in edades:
        a = dic_pop_edad[anio_censo1][edad]
        b = dic_pop_edad[anio_censo2][edad]
        if a > 0 and b > 0:
            tasa = (b / a) ** (1 / (anio_censo2 - anio_censo1)) - 1
        else:
            tasa = 0
        tasa_by_edad[edad] = tasa
    resultados["tasa_by_edad"] = tasa_by_edad

    dic_pop_potencial = {}
    for edad in edades:
        dic_pop_potencial[edad] = {}
        val_censo1 = dic_pop_edad[anio_censo1][edad]
        val_censo2 = dic_pop_edad[anio_censo2][edad]
        if val_censo2 > 0:
            base = val_censo2
            anio_base = anio_censo2
        elif val_censo1 > 0:
            base = val_censo1
            anio_base = anio_censo1
        else:
            base = 0
            anio_base = anio_censo2
        pob_base = base * (math.pi * r**2) / area
        for anio in anios_total:
            dic_pop_potencial[edad][anio] = round(pob_base * (1 + tasa_by_edad[edad]) ** (anio - anio_base))
    resultados["dic_pop_potencial"] = dic_pop_potencial
    ###################################
    # CÁLCULO DE LA EFECTIVA SIN PROYECTO
    ###################################
    # --- Proporción de matrícula sobre población potencial. Solo primer grado
    list_tasas_1g = []
    for anio in anios_hist:
        mat_1g = dic_mat_by_anio[anio][min(edades)] if dic_mat_by_anio.get(anio) and dic_mat_by_anio[anio].get(min(edades)) else 0
        pop_1g = dic_pop_potencial[min(edades)][anio] if dic_pop_potencial.get(min(edades)) and dic_pop_potencial[min(edades)].get(anio) else 0
        if mat_1g > 0:
            list_tasas_1g.append(mat_1g / pop_1g)
    if list_tasas_1g:
        prop_1g = gmean(list_tasas_1g)
    else: 
        prop_1g = 0
    resultados["prop_1g"] = prop_1g
    resultados["list_tasas_1g"] = list_tasas_1g

    # --- Tasa de transición de matriculla de un grado a otro (un año al siguiente)
    tasa_transicion = {}
    for e in edades[1:]:
        grado_ant = [dic_mat_by_anio[a][e-1] for a in anios_hist[:-1] if dic_mat_by_anio.get(a) and dic_mat_by_anio[a].get(e-1)]
        grado_post = [dic_mat_by_anio[a + 1][e] for a in anios_hist if dic_mat_by_anio.get(a + 1) and dic_mat_by_anio[a + 1].get(e)]
        tasa_transicion[e] = gmean([p / m for m, p in zip(grado_ant, grado_post) if m > 0 and p > 0]) if grado_ant and grado_post else 0
    resultados["tasa_transicion"] = tasa_transicion
    
    # --- Proyección de la matrícula efectiva sin proyecto
    dic_mat_efec_sp = {}
    anios_proy2 = list(range(datos["anio_form"] - 1, datos["anio_f"] + 1))
    for e in edades:
        dic_mat_efec_sp[e] = {}
        for a in anios_proy2:
            if a == datos["anio_form"] - 1:
                dic_mat_efec_sp[e][a] = dic_mat_by_anio[a][e] if dic_mat_by_anio.get(a) and dic_mat_by_anio[a].get(e) else 0
            elif e == min(edades):
                dic_mat_efec_sp[e][a] = round(dic_pop_potencial[e][a] * prop_1g) if prop_1g > 0 else 0
            else:
                dic_mat_efec_sp[e][a] = round(dic_mat_efec_sp.get(e-1, {}).get(a-1, 0) * tasa_transicion.get(e, 0))
    resultados["dic_mat_efec_sp"] = dic_mat_efec_sp
    
    # --- Proyección de la matrícula efectiva con proyecto
    
    # --- Promedio de la tasa de no promovidos sobre la matrícula del primer grado
    for anio in anios_hist:
        list_np = [dic_no_promv[anio][min(edades)]  if dic_no_promv.get(anio) and dic_no_promv[anio].get(min(edades)) else 0]
        list_mat = [dic_mat_by_anio[anio][min(edades)] if dic_mat_by_anio.get(anio) and dic_mat_by_anio[anio].get(min(edades)) else 0]
        list_divs = [n / m for n, m in zip(list_np, list_mat) if m > 0]
    prop_np_1g = gmean(list_divs) if list_divs else 0
    tasas_cp = {}
    for e in edades:
        if e == min(edades):
            tasas_cp[e] = prop_1g * (prop_np_1g + 1)
        else:
            tasas_cp[e] = tasa_transicion[e] if tasa_transicion[e] > 1 else 1
    resultados["tasas_cp"] = tasas_cp

    # # --- Proyección
    dic_mat_efec_cp = {}
    for e in edades:
        dic_mat_efec_cp[e] = {}
        for a in anios_proy2:
            if a == datos["anio_form"] - 1:
                dic_mat_efec_cp[e][a] = dic_mat_by_anio[a][e] if dic_mat_by_anio.get(a) and dic_mat_by_anio[a].get(e) else 0
            elif e == min(edades):
                dic_mat_efec_cp[e][a] = round(dic_pop_potencial[e][a] * tasas_cp[e]) if tasas_cp[e] > 0 else 0
            else:
                dic_mat_efec_cp[e][a] = round(dic_mat_efec_cp.get(e-1, {}).get(a-1, 0) * tasas_cp.get(e, 0))
    resultados["dic_mat_efec_cp"] = dic_mat_efec_cp
    
    ## Cálculo de aulas por edad y por turno
    aulas_by_edad = {}
    for e in edades:
        max_aulas = max([math.ceil(dic_mat_efec_cp[e][a] / est_by_aula) for a in anios_proy2]) if est_by_aula > 0 else 0 # Redondeado al entero superior
        aulas_by_edad[e] = {
            'secciones_total': math.ceil(max_aulas),
            'aulas_necesarias': (max_aulas // turnos) + (max_aulas % turnos)
        }
    resultados["aulas_by_edad"] = aulas_by_edad
    ##################################
    # ADAPTACIONES PARA EL RENDER
    ##################################
    # Tasa de crecimiento poblacional del distrito
    tasa_poptotal = resultados.get("tasa_poptotal", 0)
    tic_dist_by_dep = {
        'AMAZONAS': {'tic_dist': 0.0024458725302197804},
        'ANCASH': {'tic_dist': -0.009722077727700852},
        'APURIMAC': {'tic_dist': -0.010176041095758207},
        'AREQUIPA': {'tic_dist': 0.002698241495252799},
        'AYACUCHO': {'tic_dist': -0.01915314237340786},
        'CAJAMARCA': {'tic_dist': -0.007530965006825317},
        'CALLAO': {'tic_dist': 0.007068794294313888},
        'CUSCO': {'tic_dist': -6.320814722067003e-05},
        'HUANCAVELICA': {'tic_dist': -0.027428666320475928},
        'HUANUCO': {'tic_dist': -0.02378710461378163},
        'ICA': {'tic_dist': 0.021343104369419066},
        'JUNIN': {'tic_dist': -0.005575224112039148},
        'LA LIBERTAD': {'tic_dist': 0.0020484522421301823},
        'LAMBAYEQUE': {'tic_dist': 0.01155271401947159},
        'LIMA': {'tic_dist': -0.000993094165232594},
        'LORETO': {'tic_dist': 0.001119823964029474},
        'MADRE DE DIOS': {'tic_dist': 0.03184191249719129},
        'MOQUEGUA': {'tic_dist': -0.020255832081772174},
        'PASCO': {'tic_dist': -0.013286263519479721},
        'PIURA': {'tic_dist': 0.0050009478848328705},
        'PUNO': {'tic_dist': -0.015083404010697627},
        'SAN MARTIN': {'tic_dist': 0.012149903727460838},
        'TACNA': {'tic_dist': -0.006558413043240586},
        'TUMBES': {'tic_dist': 0.02346913477418145},
        'UCAYALI': {'tic_dist': 0.0171539403116399}        
    }
    tic_dist_by_dep[nombre_colegio.upper()] = {"tic_dist": tasa_poptotal}
    resultados["area_influencia"] = round(math.pi * r**2, 2)
    turnos = int(datos.get("turnos", 2))
    list_turnos = list(range(1, turnos + 1))
    resultados["list_turnos"] = list_turnos
    # ##################################
    # Ordenar los diccionarios 
    # ##################################
    # Solo considerar años desde el año de formulación
    anios_proy3 = list(range(datos["anio_form"], datos["anio_f"] + 1))
    for edad in edades:
        resultados["dic_mat_efec_sp"][edad] = {anio: resultados["dic_mat_efec_sp"][edad][anio] for anio in anios_proy3}
        resultados["dic_mat_efec_cp"][edad] = {anio: resultados["dic_mat_efec_cp"][edad][anio] for anio in anios_proy3}
        resultados["dic_pop_potencial"][edad] = {anio: resultados["dic_pop_potencial"][edad][anio] for anio in anios_total if anio >= datos["anio_form"]}
    # Población total y población referencial
    resultados["dic_pop_total"] = {anio: resultados["dic_pop_total"][anio] for anio in anios_total if anio >= datos["anio_form"]}
    resultados["dic_pop_ref"] = {anio: resultados["dic_pop_ref"][anio] for anio in anios_proy if anio >= datos["anio_form"]}

    # Obteener el valor mínimo de cada diccionario
    min_mat_efec_sp = min([v for d in resultados["dic_mat_efec_sp"].values() for v in d.values()])
    min_mat_efec_cp = min([v for d in resultados["dic_mat_efec_cp"].values() for v in d.values()])
    min_pop_potencial = min([v for d in resultados["dic_pop_potencial"].values() for v in d.values()])
    resultados["min_mat_efec_sp"] = min_mat_efec_sp * 0.9
    resultados["min_mat_efec_cp"] = min_mat_efec_cp * 0.9
    resultados["min_pop_potencial"] = min_pop_potencial * 0.9
    
    # Obtener la suma de valores de cada diccionario por año
    dicc = ["dic_mat_efec_sp", "dic_mat_efec_cp", "dic_pop_potencial"]
    for d in dicc:
        suma_by_anio = {}
        for anio in anios_proy3:
            suma_by_anio[anio] = sum([resultados[d][edad][anio] for edad in edades if resultados[d].get(edad) and resultados[d][edad].get(anio)])
        resultados[f"suma_tot_byaño_{d}"] = suma_by_anio
    
    # Máximo valor de las sumas
    for d in dicc:
        resultados[f"max_suma_tot_byaño_{d}"] = max(resultados[f"suma_tot_byaño_{d}"].values())
    

            
    session["datos"] = datos
    session["resultados"] = resultados
    logging.warning("Datos en paso3:\n" + pprint.pformat(datos, indent=3))
    logging.warning("Resultados en paso3:\n" + pprint.pformat(resultados, indent=3))
    return render_template(
        "paso3.html",
        datos=datos,
        resultados=resultados
    )
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)    
    
    
"""
# TÍTULO: CÁLCULO DE DEMANDA EDUCATIVA
Subtítulo: 
"""