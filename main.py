
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import re
import math
from bisect import bisect

from fastapi.responses import JSONResponse
from fastapi import APIRouter

from pydantic import BaseModel


app = FastAPI()

#app.include_router(string_api.router, prefix="/test")

cors_origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TaxesSchema(BaseModel):
    income: float = None
    medicare: float = None
    total: float = None

    @classmethod
    def create(cls, request):
        obj = cls(
            income=float(request.income),
            medicare=float(request.medicare),
            total=float(request.total)
        )

        return obj


class IncomeTaxSchema(BaseModel):
    baseSalary: float = None
    superannuation: float = None
    taxes: TaxesSchema = None
    postTaxIncome: float = None

    @classmethod
    def create(cls, request):
        obj = cls(
            baseSalary=float(request.baseSalary),
            superannuation=float(request.superannuation),
            taxes=TaxesSchema.create(request),
            postTaxIncome=float(request.postTaxIncome)
        )

        return obj


class RequestSchema(BaseModel):
    baseSalary: float = None
    superannuation: float = None
    income: float = None
    medicare: float = None
    total: float = None
    postTaxIncome: float = None


router = APIRouter()

#declarations
rates = [0, 19, 32.5, 37, 45]   # 0%, 19% etc

brackets = [18200,        # first
            37000,        # next
            87000,
            180000]        # next

base_tax = [0,               # 18200 * 0%
            3571.81,         # 37000-18201 * 19% + 0
            19821.485,       # 87000 - 37001 * 32.5 + 3571.81
            54231.115]        # 180000 -  87000 * 37% + 19821.485

medicare_rates = [0, 10, 2]
medicare_brackets = [21336,        # first
                     26, 668]                # next


net_brackets = [18200,        # first
                32688,        # next
                65438,
                122168]        # next

#---------------- Public end points -------------- #

@app.get("/reverse-words", response_model=str)
def reverse_words(sentence: str):
    return _reverse_words(sentence)


@app.get("/sort-words", response_model=str)
def sort_words(sentence: str):
    return _sort_words(sentence)


@app.get("/calculate-after-tax-income", response_model=IncomeTaxSchema)
def calculate_after_tax_income(annualBaseSalary: float):
    return _calculate_after_tax_income(annualBaseSalary)

@app.get("/calculate-pre-tax-income-from-take-home", response_model=IncomeTaxSchema)
def calc_gross(postTaxSalary: float):
    return _calc_gross(postTaxSalary)

#---------------- Private implementations -------------- #

# reverse words in a sentence
# split, reverse each word, and rejoin
# Punctuation such as full stops, exclamation marks, question marks,
# double quotes and commas should remain in postion. 
# Apostrophes in the middle or end of a word should be reversed in the same way as other characters.
def _reverse_words(input_str: str):
    try:
        # splitting the sentence on space
        subsentence_list = input_str.split()

        final_word_list = []
        for subsentence in subsentence_list:
            words_list = re.findall(
                "'\w+|\w+'\w+|\w+'|\w+|[:;,.!?\"]", subsentence)

            rev_words_list = []
            for word in words_list:
                reverse_char_list = []
                for char in range(len(word) - 1, -1, -1):
                    reverse_char_list.append(word[char])
                rev_words_list.append(''.join(reverse_char_list))
            final_word_list.append("".join(rev_words_list))

        return(" ".join(final_word_list))
    except Exception as exception:
        return JSONResponse(
            status_code=500, content={"error": str(exception)})

# sort words in a sentence
# split, sort each word, and rejoin
# Punctuation such as full stops, exclamation marks, question marks,
# double quotes and commas should remain in postion. 
# Apostrophes in the middle or end of a word should be reversed in the same way as other characters.
def _sort_words(input_str: str):
    try:
        # splitting the sentence on space
        subsentence_list = input_str.split()

        final_word_list = []
        for subsentence in subsentence_list:
            words_list = re.findall(
                "'\w+|\w+'\w+|\w+'|\w+|[:;,.!?\"]", subsentence)

            sort_words_list = []
            for word in words_list:
                sorted_char_list = sorted(word, key=lambda x: x.lower())
                sort_words_list.append(''.join(sorted_char_list))
            final_word_list.append("".join(sort_words_list))

        return(" ".join(final_word_list))
    except Exception as exception:
        return JSONResponse(
            status_code=500, content={"error": str(exception)})

#calculate total income tax
def _calc_tax(income):
    i = bisect(brackets, income)
    print(i)
    if not i:
        return 0
    rate = rates[i]
    bracket = brackets[i-1]
    income_in_bracket = income - bracket
    tax_in_bracket = income_in_bracket * rate / 100
    total_tax = base_tax[i-1] + tax_in_bracket
    print('total tax ', total_tax)
    if ((total_tax - math.floor(total_tax) - 0.159) > 0):
        total_tax = math.ceil(total_tax)
    else:
        total_tax = math.floor(total_tax)
    return total_tax

#calculate after tax income
def _calculate_after_tax_income(annualBaseSalary: float):
    try:
        superannuation = round(((9.5 * annualBaseSalary)/100), 2)
        incometax = (_calc_tax(annualBaseSalary))
        medicare_levy = 0
        if annualBaseSalary < 21336:
            medicare_levy = 0
        elif annualBaseSalary > 21336 and annualBaseSalary <= 26668:
            medicare_levy = ((annualBaseSalary - 21336) * 10) / 100
        elif annualBaseSalary > 26668:
            medicare_levy = annualBaseSalary * 2 / 100
        medicare_levy = round(medicare_levy, 2)
        totaltax = round(incometax + medicare_levy)
        postTaxIncome = annualBaseSalary - totaltax
        request = RequestSchema(
            baseSalary=annualBaseSalary,
            superannuation=superannuation,
            income=incometax,
            medicare=medicare_levy,
            total=totaltax,
            postTaxIncome=postTaxIncome
        )
        return(IncomeTaxSchema.create(request))
    except Exception as exception:
        return JSONResponse(
            status_code=500, content={"error": str(exception)})


#calculate gross income
def _calc_gross(netincome: float):
    i = bisect(net_brackets, netincome)
    #print(i)
    if not i:
        return 0
    rate = rates[i]
    bracket = brackets[i-1]
    if (netincome <= 20740):
        gross = ((100 * netincome) - (bracket * rate) +
                 (100 * base_tax[i-1])) / (100 - rate)
    elif (netincome > 20740) and (netincome <= 24526):
        gross = ((100 * netincome) - (bracket * rate) +
                 (100 * base_tax[i-1])) / (110 - rate)
    else:
        gross = ((100 * netincome) - (bracket * rate) +
                 (100 * base_tax[i-1])) / (100 - rate - 2)
    return _calculate_after_tax_income(round(gross))



#----------------- Public Endpoints --------------------------------------
@app.get("/")
def read_root():
    return Response(status_code=200)


#if __name__ == "__main__":
#    uvicorn.run(app, host="127.0.0.1", port=8000)
