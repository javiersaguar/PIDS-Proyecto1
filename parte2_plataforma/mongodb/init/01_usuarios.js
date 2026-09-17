// Se ejecuta UNA vez, al crear el volumen de MongoDB (docker compose down -v para repetirlo).
//
// Privacidad por diseño (E3): MongoDB solo guarda agregados protegidos (base `publico`) y la
// auditoría de decisiones (base `auditoria`). Los viajes individuales viven en el bucket S3 `crudo`.
// Cada componente tiene su usuario con el mínimo privilegio; la auditoría solo admite inserciones.

const env = process.env;
const admin = db.getSiblingDB('admin');

admin.createRole({
  role: 'pidsAuditoriaSoloInsertar',
  privileges: [
    { resource: { db: 'auditoria', collection: 'decisiones' }, actions: ['insert'] },
    { resource: { db: 'auditoria', collection: 'cargas' }, actions: ['insert'] },
  ],
  roles: [],
});

admin.createRole({
  role: 'pidsAuditoriaLectura',
  privileges: [
    { resource: { db: 'auditoria', collection: '' }, actions: ['find', 'listCollections'] },
  ],
  roles: [],
});

// Spark: escribe agregados y registra cada carga
admin.createUser({
  user: 'pids_spark',
  pwd: env.MONGO_SPARK_PASSWORD,
  roles: [{ role: 'readWrite', db: 'publico' }, { role: 'pidsAuditoriaSoloInsertar', db: 'admin' }],
});

// API de acceso: lee agregados y registra cada decisión de privacidad
admin.createUser({
  user: 'pids_acceso',
  pwd: env.MONGO_ACCESO_PASSWORD,
  roles: [{ role: 'read', db: 'publico' }, { role: 'pidsAuditoriaSoloInsertar', db: 'admin' }],
});

// Revisión de la auditoría (solo lectura)
admin.createUser({
  user: 'pids_auditor',
  pwd: env.MONGO_AUDITOR_PASSWORD,
  roles: [{ role: 'pidsAuditoriaLectura', db: 'admin' }],
});

const publico = db.getSiblingDB('publico');
for (const prefijo of ['', 'tr_']) {
  publico.getCollection(`${prefijo}viajes_hora_zona`).createIndex({ hora: 1, zona_origen: 1 });
  publico.getCollection(`${prefijo}viajes_dia_barrio`).createIndex({ dia: 1, barrio_origen: 1 });
  publico.getCollection(`${prefijo}od_dia_barrio`).createIndex({ dia: 1, barrio_origen: 1, barrio_destino: 1 });
}
publico.getCollection('zonas').createIndex({ nombre: 1 });

const auditoria = db.getSiblingDB('auditoria');
auditoria.createCollection('decisiones');
auditoria.decisiones.createIndex({ instante: 1 });
auditoria.decisiones.createIndex({ resultado: 1, instante: 1 });
auditoria.createCollection('cargas');

print('PIDS: usuarios, roles e índices creados');
