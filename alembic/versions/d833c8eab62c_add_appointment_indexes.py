"""add appointment indexes

Revision ID: d833c8eab62c
Revises: 479408486b50
Create Date: 2025-10-24 03:09:08.837638

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd833c8eab62c'
down_revision: Union[str, Sequence[str], None] = '479408486b50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Para búsquedas por doctor+clínica y rango de fechas (solapamientos / listados del doctor)
    op.create_index(
        "ix_appt_doctor_clinic_starts",
        "appointments",
        ["doctor_id", "clinic_id", "starts_at"],
        unique=False,
    )
    # Para listados por paciente (mis turnos del paciente)
    op.create_index(
        "ix_appt_patient",
        "appointments",
        ["patient_id"],
        unique=False,
    )

    # Para rangos de fecha (filtros date_from/date_to)
    op.create_index(
        "ix_appt_starts",
        "appointments",
        ["starts_at"],
        unique=False,
    )

    # Útil cuando filtrás solo por clínica (admin)
    op.create_index(
        "ix_appt_clinic",
        "appointments",
        ["clinic_id"],
        unique=False,
    )

    # (Opcional) Si filtrás por estado a menudo
    op.create_index(
        "ix_appt_status",
        "appointments",
        ["status"],
        unique=False,
    )

    # (Opcional extra) Acelera más aún el check de solapamiento según motor
    # op.create_index(
    #     "ix_appt_doctor_clinic_ends",
    #     "appointments",
    #     ["doctor_id", "clinic_id", "ends_at"],
    #     unique=False,
    # )

def downgrade() -> None:
    # Borrar en orden inverso
    # op.drop_index("ix_appt_doctor_clinic_ends", table_name="appointments")  # si lo cree
    op.drop_index("ix_appt_status", table_name="appointments")
    op.drop_index("ix_appt_clinic", table_name="appointments")
    op.drop_index("ix_appt_starts", table_name="appointments")
    op.drop_index("ix_appt_patient", table_name="appointments")
    op.drop_index("ix_appt_doctor_clinic_starts", table_name="appointments")

