# Asistente de datos de taxis (RAG)

Consulta agregados de los viajes de taxi amarillo de Nueva York (2020). La plataforma aplica
privacidad total: no se muestran viajes ni personas concretas, y los grupos con muy pocos viajes
aparecen enmascarados.

Esta versión recupera primero el conocimiento de la plataforma (documentación, zonas, ejemplos y
fichas de agregados por día y barrio) y pide las cifras exactas a la API de acceso. En cada respuesta,
el desplegable «Fuentes» dice qué se ha usado y cuántos tokens ha costado el turno.
