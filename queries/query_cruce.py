def get_query_cruce():
    query = """
-- CTE que consolida la existencia de inventario en BODEGA_DATOS
WITH BodegaCTE AS (
    SELECT 
        LTRIM(RTRIM(tbDimInventario.CodigoBarra)) AS CleanCodigoBarra,
        CASE
            WHEN tbDimInventario.dimID_Inventario IN (2003) THEN 'Valencia Casa Matriz'
            WHEN tbDimInventario.dimID_Inventario IN (2005) THEN 'Oriente - Casa Matriz'
            WHEN tbDimInventario.dimID_Inventario IN (
                1, 1002, 1004, 1006, 1007, 1008, 1009, 1010, 1011, 1012,
                1013, 1014, 1015, 1016, 1017, 1018, 1019, 1020, 1021, 1022,
                1023, 1024, 1025, 1058)
                THEN 'Oriente - Sucursales'
            WHEN tbDimInventario.dimID_Inventario IN (2004) THEN 'Occidente - Casa Matriz'
            WHEN tbDimInventario.dimID_Inventario IN (
                1026,1027,1028,1029,1030,1031,1037,1038,1039,1040,
                1041,1042,1043,1044,1045,1046,1047,1048,1049,1050,
                1051,1052,1053,1054,1055,2007)
                THEN 'Occidente - Sucursales'
            WHEN tbDimInventario.dimID_Inventario IN (2006) THEN 'Margarita - Casa Matriz'
            WHEN tbDimInventario.dimID_Inventario IN (1032,1033,1034,1035,1036)
                THEN 'Margarita - Sucursales'
            ELSE 'Sin región'
        END AS Region,
        SUM(tbHecInventario.Existencia) AS Existencia_Total
    FROM [BODEGA_DATOS].dbo.tbDimInventario
    LEFT JOIN [BODEGA_DATOS].dbo.tbHecInventario 
        ON tbDimInventario.dimID_Inventario = tbHecInventario.dimid_inventario
    LEFT JOIN [BODEGA_DATOS].dbo.tbDimFabricantes F 
        ON F.Codigo = tbDimInventario.Fabricante
    WHERE tbHecInventario.Existencia > 0
    GROUP BY LTRIM(RTRIM(tbDimInventario.CodigoBarra)), tbDimInventario.dimID_Inventario
),

-- CTE que obtiene datos de transferencias e INVENTARIO en J101010100_999911
CreacionCTE AS (
    SELECT 
        LTRIM(RTRIM(I.Referencia)) AS CleanReferencia,
        I.CodigoBarra,
        I.CodigoMarca,
        M.Nombre AS Marca,
        I.Nombre,
        COALESCE(F.Nombre, '') AS Nombre_Fabricante,
        COALESCE(F.Codigo, '') AS CodigoFabricante,
        LEFT(C.Codigo, 4) AS CategoriaCodigo,
        C.Nombre AS CategoriaNombre,
        CC.Nombre AS Linea,
        MT.Cantidad AS Cantidad,
        CASE WHEN T.correccion = 1 THEN 1 ELSE 0 END AS correccion,
        MT.Numero AS NumeroTransferencia,
        CAST(T.Fecha AS DATE) AS FechaLlegada,  -- se conserva solo la fecha, sin hora
        COALESCE(T.observacion, '') AS observacion
    FROM [J101010100_999911].dbo.MOVTRANSFERENCIAS MT
    RIGHT JOIN [J101010100_999911].dbo.INVENTARIO I
        ON I.CodigoBarra = MT.CodigoBarra
    RIGHT JOIN [J101010100_999911].dbo.CATEGORIAS C
        ON I.Categoria = C.Codigo
    LEFT JOIN [J101010100_999911].dbo.MARCAS M
        ON I.CodigoMarca = M.Codigo
    LEFT JOIN [J101010100_999911].dbo.CATEGORIAS CC
        ON LEFT(C.Codigo, 4) = CC.Codigo
    INNER JOIN [J101010100_999911].dbo.TRANSFERENCIAS T
        ON T.numero = MT.numero
    INNER JOIN [J101010100_999911].dbo.FABRICANTES F
        ON F.Codigo = I.Fabricante
    -- Utiliza el parámetro :fechaStart para definir el inicio del rango y GETDATE() como final
    WHERE T.Fecha BETWEEN :fechaStart AND GETDATE()
      AND T.CodigoRecibe <> 'J-40610499-0'
),

-- CTE que agrupa los datos y asocia inventario con transferencias 
-- Agrupando por CódigoBarra y FechaLlegada
FinalCTE AS (
    SELECT 
        MAX(c.CleanReferencia) AS CleanReferencia,
        c.CodigoBarra,
        MAX(c.CodigoMarca) AS CodigoMarca,
        MAX(c.Marca) AS Marca,
        MAX(c.Nombre) AS Nombre,
        MAX(c.Nombre_Fabricante) AS Nombre_Fabricante,
        MAX(c.CodigoFabricante) AS CodigoFabricante,
        MAX(c.CategoriaCodigo) AS CategoriaCodigo,
        MAX(c.CategoriaNombre) AS CategoriaNombre,
        MAX(c.Linea) AS Linea,
        SUM(c.Cantidad) AS CantidadInicial,
        SUM(c.Cantidad) AS Cantidad_Inicial_Agrupada,
        MAX(b.Existencia_Total) AS ExistenciaActual,
        MAX(c.correccion) AS correccion,
        MAX(c.NumeroTransferencia) AS NumeroTransferencia,
        c.FechaLlegada,
        MAX(c.observacion) AS observacion
    FROM CreacionCTE c
    LEFT JOIN BodegaCTE b 
        ON c.CodigoBarra = b.CleanCodigoBarra
    WHERE c.Cantidad > 1
    GROUP BY c.CodigoBarra, c.FechaLlegada
),

-- CTE final para formatear números en la presentación
Final2 AS (
    SELECT 
        *,
        -- En Queda y Vendido, si la división es inválida se devuelve COALESCE para mostrar '0%'
        CASE 
            WHEN Cantidad_Inicial_Agrupada = 0 THEN '0%'
            ELSE FORMAT(ExistenciaActual * 100.0 / NULLIF(Cantidad_Inicial_Agrupada, 0), 'N2') + '%'
        END AS Queda,
        CASE 
            WHEN Cantidad_Inicial_Agrupada = 0 THEN '0%'
            ELSE FORMAT(100.0 - (ExistenciaActual * 100.0 / NULLIF(Cantidad_Inicial_Agrupada, 0)), 'N2') + '%'
        END AS Vendido
    FROM FinalCTE
)

SELECT 
    CleanReferencia AS Referencia,
    CodigoBarra,
    CodigoMarca,
    Marca,
    Nombre,
    Nombre_Fabricante,
    CodigoFabricante,
    CategoriaCodigo,
    CategoriaNombre,
    Linea,
    ISNULL(CantidadInicial, 0) AS CantidadInicial,
    ISNULL(Cantidad_Inicial_Agrupada, 0) AS Cantidad_Inicial_Agrupada,
    ISNULL(ExistenciaActual, 0) AS ExistenciaActual,
    correccion,
    NumeroTransferencia,
    FechaLlegada,
    observacion,
    COALESCE(Queda, '0%') AS Queda,
    COALESCE(Vendido, '0%') AS Vendido
FROM Final2;
    """
    return query
