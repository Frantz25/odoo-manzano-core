# Instalación de módulos — Orden 1 a 1 (obligatorio)

**Regla:** instalar un módulo por vez, validar, luego continuar.

## Orden recomendado
1. `cer_base`
2. `cer_catalog_github`
3. `cer_pricing`
4. `cer_booking`
5. `cer_documents`
6. `cer_communications`
7. `manzano_catalog`
8. `manzano_booking`
9. `manzano_catalog_integration`

## Comando base por módulo
```bash
docker compose exec -T odoo odoo -d manzano_dev -c /etc/odoo/odoo.conf --db_host=db --db_user=odoo --db_password=odoo_manzano_pw -i <modulo> --stop-after-init
docker compose restart odoo
```

## Validación mínima por módulo
- Instala sin traceback.
- Modelo principal visible en UI.
- Vista principal abre sin error Owl/QWeb.
- Acción principal ejecuta al menos 1 caso positivo.

## Nota
No se borra ningún módulo existente. Este repositorio mantiene módulos `cer_*` como referencia/panorama y módulos `manzano_*` como implementación activa del plan actual.
