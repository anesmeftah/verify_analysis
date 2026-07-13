import re
from dataclasses import dataclass

@dataclass
class test_result:
    start_idx : int
    end_idx : int
    file_path : str

    @property
    def start_idx(self , start):
        self.start_idx = start

    @property
    def end_idx(self, end):
        self.end_idx = end


    @property
    def file_path(self , path):
        self.file_path = path

    
    



def parser(file_path : str):

    tests = {}
    test = test_result(file_path=file_path)
    idx_pattern = re.compile(r"idx:\s*(\d+)")
    result_pattern = re.compile(r"Result:")
    with open(file=file_path , mode='r') as f:
        for line in f:
            idx = idx_pattern.search(line)
            if idx:
                test.start_idx = f.tell()
                tests[idx] = test

            result = result_pattern.search(line)
            if result:
                test.end_idx = f.tell()
                test = test_result(file_path=file_path)
            
    f.close()
    return tests

def check_type(text : str):
    number_violation_pattern = r"Total number of violation:\s*(\d+)"
    number = re.search(number_violation_pattern, text)
    if  number != 0:
        return "CE"
    BaB_pattern = r"prune_after_crown optimization in use"
    match = re.search(BaB_pattern , text)
    if match:
        return "BaB"
    else:
        return "AC"


def get_test_summary(tests_dic : dict[int , test_result] , id : int):
    test = tests_dic[id] 

    bytes_to_read = test.end_idx - test.start_idx
    with open(file=test.file_path , mode='r') as f:
        f.seek(test.start_idx)

        text = f.read(bytes_to_read)  # noqa: F841
    
    f.close()
    types = ["CE" , "AC" , "BaB"]
    Type = check_type(text)

    if Type == types[0]:
        pass
    elif Type == types[1]:
        pass
    else:
        pass

    pass
            