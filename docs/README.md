
# Entrega 3 - Módulo de Extracción de Landmarks con MediaPipe Integrado 

Este repositorio contiene el código fuente de un proyecto de tesis cuyo objetivo es desarrollar e investigar métodos para la extracción, normalización y análisis de landmarks (puntos clave) de la mano usando MediaPipe en el frontend y procesamiento numérico en el backend.

## Integrantes

- Catalina Alejandra Quijano Lopez
- Mariam Daniela Gutierrez Alfonso
- Edwin Alejandro Rodriguez Zubieta

*(Sustituya los marcadores anteriores por los integrantes reales del grupo.)*

## Propósito del proyecto

El propósito central de la tesis es:

- Construir una canalización (pipeline) completa que capture vídeo desde la cámara del navegador, detecte landmarks de la mano en el cliente (MediaPipe JS), y envíe los datos al servidor para su procesamiento.
- Definir y evaluar transformaciones/normalizaciones que hagan los landmarks comparables entre diferentes capturas (por tamaño, posición y orientación), y extraer características como ángulos articulares y vector normal de la palma.
- Facilitar experimentos y análisis (por ejemplo, reconocimiento de gestos o lecturas biométricas de postura manual) mediante una API reproducible y una base de procesamiento numérico en Python.

## Especificación de la API

La especificación completa de la API, los formatos de payload y ejemplos se encuentran en:

[Especificación de la API (API_SPEC.md)](API_SPEC.md)

> Nota: `API_SPEC.md` contiene ejemplos de request/response, instrucciones de ejecución y notas de depuración.

## Cómo usar (rápido)

1. Siga las instrucciones de `docs/API_SPEC.md` para instalar dependencias y arrancar el servidor.
2. Abra `http://127.0.0.1:8000/` en su navegador, permita el acceso a la cámara y pruebe la detección en la interfaz.
3. Use el botón para enviar landmarks al endpoint `/extract` y ver la respuesta con las características calculadas.
