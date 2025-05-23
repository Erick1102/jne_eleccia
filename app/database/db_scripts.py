"""Scripts para extraer informarción espeficia de la base de datos."""

from sqlalchemy import text

#obtener documentos
Documentos = text("""
                    WITH Expediente AS (
                        SELECT IDEXPEDIENTE, TXCODIGODECLARA 
                        FROM SIJE.SIJE_TBL_EXPEDIENTE 
                        WHERE TXCODEXPEDIENTEEXT = :TXCODEXPEDIENTEEXT
                    )
                    SELECT 
                        mtted.IDTRAMITEESCRITO, 
                        mtted.IDARCHIVO, 
                        mtted.TXCODARCHIVO, 
                        mtted.IDSUBTIPODOCUMENTO, 
                        mtted.TXDESCRIPCION, 
                        mta.IDARCHIVO, 
                        mta.TXRUTA, 
                        'https://mpesije.jne.gob.pe/docs/' || mta.TXNOMBRE AS TXRUTAVIRTUAL
                    FROM MPE.MPE_TBL_TRAMITE mp
                    JOIN MPE.MPE_TBL_TRAMITE_ESCRITO mpt ON mpt.IDTRAMITE = mp.IDTRAMITE
                    JOIN MPE.MPE_TBL_TRAMITE_ESCRITO_DOCS mtted ON mtted.IDTRAMITEESCRITO = mpt.IDTRAMITEESCRITO
                    JOIN MPE.MPE_TBL_ARCHIVO mta ON mta.IDARCHIVO = mtted.IDARCHIVO
                    JOIN (SELECT * FROM Expediente) e ON mp.IDEXPEDIENTE = e.IDEXPEDIENTE
                    WHERE mp.IDTIPOEXPEDIENTE = 13 
                    AND mp.IDMATERIA = 27 
                    AND mp.IDPROCESOELECTORAL = 113
                    AND mtted.IDSUBTIPODOCUMENTO IN (13, 8, 7, 3)
                """)

#obtener candidatos
Candidatos = text("""
                    WITH Expediente AS (
                        SELECT IDEXPEDIENTE, TXCODIGODECLARA 
                        FROM SIJE.SIJE_TBL_EXPEDIENTE
                        WHERE TXCODEXPEDIENTEEXT = :TXCODEXPEDIENTEEXT
                    )

                    SELECT 
                        sc.IDCANDIDATOS, 
                        c.IDSOLICITUDLISTA, 
                        c.IDHOJAVIDA,    
                        dp.TXDOCUMENTOIDENTIDAD, 
                        dp.TXAPELLIDOPATERNO, 
                        dp.TXAPELLIDOMATERNO, 
                        dp.TXNOMBRES, 
                        dp.TXSEXO, 
                        dp.FENACIMIENTO,
                        c.NUEDAD,
                        dp.TXUBIGEODOMICILIO,
                        dp.TXDOMIDEPARTAMENTO ||'/'|| dp.TXDOMIPROVINCIA ||'/'|| dp.TXDOMIDISTRITO AS TXDIRECCIONREGION,
                        dp.TXDOMICILIODIRECC,
                        ce.TXCARGOELECCION,
                        dp.TXUBIGEOPOSTULA,
                        dp.TXPOSTULADEPARTAMENTO ||'/'|| dp.TXPOSTULAPROVINCIA ||'/'|| dp.TXPOSTULADISTRITO AS TXPOSTULAREGION,    
                        sc.IDESTADO,
                        sc.NUPOSICION,
                        c.FGNATIVO,
                        dp.TXPAISNACIMIENTO,
                        dtop.TXORGANIZACIONPOLITICA,
                        dtl.NUTOTALMIEMBROS
                    FROM DECLARA.DECA_TBL_CANDIDATO c
                    INNER JOIN DECLARA.DECA_TBL_SOLICITUD_LISTA sl ON c.IDSOLICITUDLISTA = sl.IDSOLICITUDLISTA
                    INNER JOIN DECLARA.DECA_TBL_HVDATOSPERSONALES dp ON c.IDHOJAVIDA = dp.IDHOJAVIDA
                    INNER JOIN DECLARA.DECA_TRF_CARGO_ELECCION ce ON c.IDCARGOELECCION = ce.IDCARGOELECCION
                    INNER JOIN sije.SIJE_TBL_CANDIDATOS sc ON sc.IDCANDIDATODECLARA = c.IDCANDIDATO
                    INNER JOIN DECLARA.DECA_TBL_ORGANIZACION_POLITICA dtop ON dtop.IDORGANIZACIONPOLITICA = sl.IDORGANIZACIONPOLITICA
                    INNER JOIN DECLARA.DECA_TBL_LISTACONFIGUBIGEO dtl ON sl.TXUBIGEOPOSTULA = dtl.TXUBIGEO
                    INNER JOIN (SELECT * FROM Expediente) e ON sl.TXCODSOLICITUDLISTA = e.TXCODIGODECLARA
                    WHERE sc.IDESTADO IN (4, 8, 11)
                    ORDER BY sc.NUPOSICION ASC
                """)

#obtener documentos de los candidatos
Documentos_candidato = text("""
                                WITH Expediente AS (
                                    SELECT IDEXPEDIENTE, TXCODIGODECLARA 
                                    FROM sije.SIJE_TBL_EXPEDIENTE 
                                    WHERE TXCODEXPEDIENTEEXT = :TXCODEXPEDIENTEEXT
                                )

                                SELECT 
                                    sc.IDCANDIDATOS, 
                                    c.IDSOLICITUDLISTA, 
                                    c.IDHOJAVIDA,
                                    c.TXDOCUMENTOIDENTIDAD, 
                                    dp.IDDOCUMENTO,
                                    dtda.TXNOMBRE,
                                    sc.IDESTADO,
                                    'https://mpesije.jne.gob.pe/apidocs/' || dp.TXGUIDARCHIVOADJ || '.pdf' AS TXRUTAVIRTUAL,   
                                    ce.TXCARGOELECCION,   
                                    sc.NUPOSICION,
                                    dp.FECARGA
                                FROM DECLARA.DECA_TBL_CANDIDATO c
                                INNER JOIN DECLARA.DECA_TBL_SOLICITUD_LISTA sl ON c.IDSOLICITUDLISTA = sl.IDSOLICITUDLISTA
                                INNER JOIN DECLARA.DECA_TBL_HVDOCUMENTOS dp ON c.IDHOJAVIDA = dp.IDHOJAVIDA
                                INNER JOIN DECLARA.DECA_TRF_CARGO_ELECCION ce ON c.IDCARGOELECCION = ce.IDCARGOELECCION
                                INNER JOIN DECLARA.DECA_TBL_DOCUMENTO_ADJ dtda ON dp.IDDOCUMENTO = dtda.IDDOCUMENTO
                                INNER JOIN sije.SIJE_TBL_CANDIDATOS sc ON sc.IDCANDIDATODECLARA = c.IDCANDIDATO
                                INNER JOIN Expediente e ON sl.TXCODSOLICITUDLISTA = e.TXCODIGODECLARA
                                WHERE sc.IDESTADO IN (4,8,11) AND dp.IDDOCUMENTO IN (1,2,3,4,5,6,7,8,9,10) AND dp.IDESTADO = 1
                                ORDER BY sc.NUPOSICION, dp.IDDOCUMENTO ASC
                            """)

#obtener personero
Personero = text("""
                    WITH Expediente AS (
                        SELECT IDEXPEDIENTE, TXCODIGODECLARA 
                        FROM SIJE.SIJE_TBL_EXPEDIENTE 
                        WHERE TXCODEXPEDIENTEEXT = :TXCODEXPEDIENTEEXT
                    )

                    SELECT 
                        p.IDPERSONERO, 
                        p.TXNOMBRE, 
                        p.TXAPELLIDO, 
                        p.TXDIRECCION, 
                        p.TXTELEFONO, 
                        p.TXEMAIL, 
                        p.TXTIPOIDENTIFICACION, 
                        p.TXNUMEROIDENTIFICACION
                    FROM SIJE.SIJE_TBL_PERSONERO p
                    INNER JOIN (SELECT * FROM Expediente) e ON p.IDEXPEDIENTE = e.IDEXPEDIENTE
                """)

#obtener expediente sije
Expediente_sije = text("""
                        SELECT IDEXPEDIENTE, IDMATERIA, IDTIPOEXPEDIENTE
                        FROM sije.SIJE_TBL_EXPEDIENTE 
                        WHERE TXCODEXPEDIENTEEXT = :TXCODEXPEDIENTEEXT
                        """)

#obtener resumen plan de gobierno
Resumen_PG = text("""
                    WITH Expediente AS (
                        SELECT IDEXPEDIENTE, TXCODIGODECLARA 
                        FROM sije.SIJE_TBL_EXPEDIENTE 
                        WHERE TXCODEXPEDIENTEEXT = :TXCODEXPEDIENTEEXT
                    )

                    SELECT
                        dtop.TXORGANIZACIONPOLITICA,
                        dtp.TXIDEARIO,
                        dtp.TXVISION,
                        dtpd.TXPGPROBLEMA,
                        dtpd.TXPGOBJETIVO,
                        dtpd.TXPGMETA,
                        dtpd.TXPGINDICADOR, --indicador
                        dtpd.IDPGDIMENSION 
                    FROM DECLARA.DECA_TBL_PLANGOBIERNO dtp 
                    INNER JOIN DECLARA.DECA_TBL_PLANGOB_DIMENSION dtpd ON dtp.IDPLANGOBIERNO = dtpd.IDPLANGOBIERNO
                    INNER JOIN DECLARA.DECA_TBL_SOLICITUD_LISTA dtsl  ON dtp.IDSOLICITUDLISTA = dtsl.IDSOLICITUDLISTA
                    INNER JOIN DECLARA.DECA_TBL_ORGANIZACION_POLITICA dtop ON dtop.IDORGANIZACIONPOLITICA = dtsl.IDORGANIZACIONPOLITICA 
                    INNER JOIN Expediente e ON dtsl.TXCODSOLICITUDLISTA = e.TXCODIGODECLARA
                    ORDER BY dtpd.IDPGDIMENSION ASC
                """)

#consulta ROP
Consulta_ROP = text(""" 
                    CALL COMPARTIDO.PKG_AFILIACION_RRHH.SP_LISTAR_CONS4ANOS_DNI(:DNI, ?) 
                    """)
