"""add uniq + link indexes

Revision ID: 380fb8384de4
Revises: d833c8eab62c
Create Date: 2025-10-24 03:30:54.159149

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '380fb8384de4'
down_revision: Union[str, Sequence[str], None] = 'd833c8eab62c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
     # clinic_doctors
    op.create_unique_constraint("uq_clinic_doctor", "clinic_doctors", ["clinic_id", "doctor_id"])
    op.create_index("ix_clinic_doctor_clinic", "clinic_doctors", ["clinic_id"])
    op.create_index("ix_clinic_doctor_doctor", "clinic_doctors", ["doctor_id"])

    # clinic_patients
    op.create_unique_constraint("uq_clinic_patient", "clinic_patients", ["clinic_id", "patient_id"])
    op.create_index("ix_clinic_patient_clinic", "clinic_patients", ["clinic_id"])
    op.create_index("ix_clinic_patient_patient", "clinic_patients", ["patient_id"])

def downgrade() -> None:
    op.drop_index("ix_clinic_patient_patient", table_name="clinic_patients")
    op.drop_index("ix_clinic_patient_clinic", table_name="clinic_patients")
    op.drop_constraint("uq_clinic_patient", "clinic_patients", type_="unique")

    op.drop_index("ix_clinic_doctor_doctor", table_name="clinic_doctors")
    op.drop_index("ix_clinic_doctor_clinic", table_name="clinic_doctors")
    op.drop_constraint("uq_clinic_doctor", "clinic_doctors", type_="unique")