from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class DayCare(BaseModel):
    day_care_treatment: str

class MaternityFull(BaseModel):
    no_of_deliveries: str
    limit_normal_delivery: str
    limit_C_Section: str
    waiting_period: str

class Natel(BaseModel):
    pre_natal: str
    post_natal: str

class Corporate(BaseModel):
    primary_insured_members: str
    total_sum_insured: str

class Refractive(BaseModel):
    si_limit: str
    eye_power: float = Field(description="may be mentioned in dioptres")

class Mental(BaseModel):
    benefit_limit: str

class CoPay(BaseModel):
    policy_co_payment_factor: str = Field(description="may be mentioned as a percentage, and can include conditions, "
                                                      "so output the appropriate value")
    co_pay_type: str = Field(description="refers to types of claims and hospitals")


class Ambulance(BaseModel):
    road_ambulance_limit: str
    road_ambulance_limit_covid: str


class PolicyPeriod(BaseModel):
    start_date: date
    end_date: date

class AAYUSH(BaseModel):
    ayush_treatment_limit: str

class PreHosp(BaseModel):
    pre_hospitalization_period: str

class PostHosp(BaseModel):
    post_hospitalization_period: str

class PreExisting(BaseModel):
    pre_existing_disease_wait_period: str

class Policy(BaseModel):
    policy_number: str
    name_policyholder: str
    policy_start_date: str
    policy_end_date: str
class RoomRent(BaseModel):
    sum_insured: str = Field(description="can be under the heading Room Rent under Sum Insured column")
    maximum_eligibility_for_normal_hospitalization: str = Field(description="can be under the heading Room Rent under Maximum eligibility for Normal Hospitalization column")
    maximum_eligibility_for_icu_hospitalization: str = Field(description="can be under the heading Room Rent under Maximum eligibility for ICU Hospitalization column")

class Benefits(BaseModel):
    medical_expences: str = Field(description="Under Benefits heading")
    any_one_accident_limit: str = Field(description= "some times may be written as AOA limit")
    accidental_death: str = Field(description= "Present under the benefits section")
    funeral_expenses: str

class OutputFull(BaseModel):
    policy_details: Policy 
    day_care_treatment: DayCare
    pre_and_post_natal_expenses: Natel
    maternity_expenses: MaternityFull
    corporate_buffer: Corporate
    refractive_error_correction_expenses: Refractive
    mental_illness: Mental
    co_pay: CoPay
    road_ambulance: Ambulance
    ayush_treatment: AAYUSH
    pre_hospitalization: PreHosp
    post_hospitalization: PostHosp
    pre_existing_disease: PreExisting
    room_rent_details: RoomRent
    benefits_and_other: Benefits




