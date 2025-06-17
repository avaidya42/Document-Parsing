from enum import Enum
from pydantic import BaseModel, Field

class DayCare(BaseModel):
    day_care_treatment: str

class OrganDonor(BaseModel):
    organ_donor_expenses: str

class NatalIPD(BaseModel):
    expenses_limit_IPD: str
    applicability: str

class Maternity(BaseModel):
    no_of_deliveries: str

class MaternityFull(BaseModel):
    no_of_deliveries: str
    limit_normal_delivery: str
    limit_C_Section: str
    waiting_period: str

class NatalOPD(BaseModel):
    expenses_limit_OPD: str

class Corporate(BaseModel):
    sum_insured: str
    type_of_ailment: str
    type_of_coverage: str

class Refractive(BaseModel):
    si_limit: str
    eye_power: float = Field(description="may be mentioned in dioptres")

class HIV(BaseModel):
    hiv_anti_retroviral_therapy: str

class Nursing(BaseModel):
    per_week_benefit: str = Field(description="convert allowance amount to per week (times 7) if given as per day")
    number_of_weeks: str = Field(description="convert duration to number of weeks (divided by 7, return nearest "
                                             "integer) if given in number of days")

class Preventive(BaseModel):
    benefit_limit: str
    clinic_options: str

class OPD(BaseModel):
    benefit_limit: str

class Physiotherapy(BaseModel):
    benefit_limit: str
    coverage_type: str

class Dental(BaseModel):
    benefit_limit: str

class Mental(BaseModel):
    benefit_limit: str

class Vision(BaseModel):
    benefit_limit: str

class Obesity(BaseModel):
    obesity_control_coverage: str

class CoPay(BaseModel):
    policy_co_payment_factor: str = Field(description="may be mentioned as a percentage, and can include conditions, "
                                                      "so output the appropriate value")
    co_pay_type: str = Field(description="refers to types of claims and hospitals")

class Room(BaseModel):
    room_rent_limit: str = Field(description="may be in the form of a number or a percentage of SI, if it is "
                                             "different for general, and ICU, mention the entire condition")
    options_for_deductions: str = Field(description="as 'Proportionate Deduction', or 'Capping on Room Charges only', "
                                                    "only consider the normal case, do not consider the case for "
                                                    "ICU hospitalization or cases where there is no differential "
                                                    "billing.")

class Ambulance(BaseModel):
    road_ambulance_limit: str

class AAYUSH(BaseModel):
    ayush_treatment_limit: str

class MedAdv(BaseModel):
    medical_advancement_surgery_limit: str

class PreHosp(BaseModel):
    pre_hospitalization_period: str

class PostHosp(BaseModel):
    post_hospitalization_period: str

class PreExisting(BaseModel):
    pre_existing_disease_and_specified_disease_waiting_period: str

class Extra(BaseModel):
    policy_number: str
    name_policyholder: str
    policy_start_date: str
    policy_end_date: str
    primary_insured_members: str

class Output(BaseModel):
    day_care_treatment: DayCare
    organ_donor_expenses: OrganDonor
    pre_and_post_natal_expenses_IPD: NatalIPD = Field(description="Must be taken from pre and post natal section or "
                                                                  "other conditions section of the data.")
    maternity_expenses: Maternity
    pre_and_post_natal_expenses_OPD: NatalOPD = Field(description="Must be taken from pre and post natal section or "
                                                                  "other conditions section of the data.")
    corporate_buffer: Corporate = Field(description="Values must be taken from the corporate buffer section. If not "
                                                    "present, do not fill corporate_buffer['sum_insured']. If present, "
                                                    "type_of_ailment and type_of_coverage may also be mentioned here.")
    refractive_error_correction_expenses: Refractive = Field(description="mentioned under Other Conditions (sometimes "
                                                                         "under pre and post natal) and may "
                                                                         "sometimes be labeled as lasik")
    hiv_anti_retroviral_therapy: HIV
    home_nursing_benefit: Nursing
    preventive_health_check_up: Preventive
    opd_expenses: OPD
    physiotherapy_on_opd_basis: Physiotherapy
    dental_care: Dental
    mental_illness: Mental
    vision_expenses_cover: Vision
    obesity_control_coverage: Obesity
    co_pay: CoPay
    room_rent: Room = Field(description="If asked to refer to claim condition, they will be under Room Rent Restriction")
    road_ambulance: Ambulance
    ayush_treatment: AAYUSH = Field(description="may be mentioned under Ayurveda, Yoga & Naturopathy, Unani, Siddha, "
                                                "Sowa Rigpa and Homoeopathy")
    medical_advancement_surgery: MedAdv = Field(description="may be mentioned as Modern Treatment Methods and "
                                                            "Advancement in Technologies under Other Conditions or "
                                                            "for Cyberknife treatment, Stem Cell Transplantation, "
                                                            "Cochlear Implant")

class OutputFull(BaseModel):
    day_care_treatment: DayCare
    organ_donor_expenses: OrganDonor
    pre_and_post_natal_expenses_IPD: NatalIPD
    maternity_expenses: MaternityFull
    pre_and_post_natal_expenses_OPD: NatalOPD
    corporate_buffer: Corporate
    refractive_error_correction_expenses: Refractive
    hiv_anti_retroviral_therapy: HIV
    home_nursing_benefit: Nursing
    preventive_health_check_up: Preventive
    opd_expenses: OPD
    physiotherapy_on_opd_basis: Physiotherapy
    dental_care: Dental
    mental_illness: Mental
    vision_expenses_cover: Vision
    obesity_control_coverage: Obesity
    co_pay: CoPay
    room_rent: Room
    road_ambulance: Ambulance
    ayush_treatment: AAYUSH
    medical_advancement_surgery: MedAdv
    pre_hospitalization: PreHosp
    post_hospitalization: PostHosp
    pre_existing_disease_and_specified_disease: PreExisting
    extra : Extra

