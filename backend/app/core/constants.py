"""
Barcha magic stringlar, doimiy matnlar va konfiguratsiya konstantalari shu yerda saqlanadi.
"""

class ErrorMessages:
    # Umumiy xatoliklar
    NOT_FOUND = "Topilmadi"
    UNAUTHORIZED = "Ruxsat etilmagan"
    BAD_REQUEST = "Noto'g'ri so'rov"
    
    # Application xatoliklari
    APPLICATION_NOT_FOUND = "Ariza topilmadi"
    INVALID_NUMBER_VALUE = "Raqamli qiymat noto'g'ri (min/max oralig'ida emas)"
    REQUIRED_FIELD_MISSING = "Majburiy maydon to'ldirilmagan: {field}"
    
    # Scholarship xatoliklari
    SCHOLARSHIP_NOT_FOUND = "Stipendiya topilmadi"
    INVALID_STATUS_TRANSITION = "Holat faqat '{current}' -> '{expected}' bo'lishi mumkin"
    FINAL_STATUS_REACHED = "Yakuniy holatga yetilgan"
    NO_ACTIVE_STAGE = "Hozir faol bosqich yo'q"
    INVALID_ACTIVE_STAGE = "Hozir '{active}' bosqichi faol. Ruxsat berilgan bosqichlar: {allowed}"
    
    # Ustun/Hakam xatoliklari
    COLUMN_NOT_FOUND = "Ustun topilmadi"
    INVALID_MIN_MAX = "Number ustunida min qiymat max qiymatdan katta bo‘lishi mumkin emas"
    JURY_NOT_FOUND = "Hakam topilmadi"
    JURY_ASSIGNMENT_NOT_FOUND = "Biriktirish topilmadi"


class SuccessMessages:
    ORDER_UPDATED = "Tartib yangilandi"
    JURY_ASSIGNED = "Hakam biriktirildi"
