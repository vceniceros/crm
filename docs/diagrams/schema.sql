CREATE TABLE Usuarios(
    id_usuario UUID PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    contraseña VARCHAR(255) NOT NULL,
    rol VARCHAR(50) NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso TIMESTAMP
);

CREATE TABLE Clientes(
    id_cliente UUID PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    telefono VARCHAR(20),
    latitud FLOAT,
    longitud FLOAT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Productos(
    id_producto UUID PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    stock INT NOT NULL,
    url_imagen VARCHAR(255),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE Solicitud_producto(
    id_solicitud_producto UUID PRIMARY KEY,
    id_producto UUID REFERENCES Productos(id_producto) ON DELETE CASCADE,
    cantidad INT NOT NULL,
    usuario_solicitante UUID REFERENCES Usuarios(id_usuario) ON DELETE SET NULL,
    fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Productos_entregados(
    id_solicitud_producto UUID PRIMARY KEY REFERENCES Solicitud_producto(id_solicitud_producto) ON DELETE CASCADE,
    id_usuario_entrega UUID REFERENCES Usuarios(id_usuario) ON DELETE SET NULL,
    codigo_de_barras VARCHAR(255) NOT NULL,
    fecha_entrega TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

CREATE TABLE Visitas(
    id_visita UUID PRIMARY KEY,
    id_cliente UUID REFERENCES Clientes(id_cliente) ON DELETE CASCADE,
    id_usuario UUID REFERENCES Usuarios(id_usuario) ON DELETE SET NULL,
    fecha_visita TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    latitud FLOAT,
    longitud FLOAT
);

