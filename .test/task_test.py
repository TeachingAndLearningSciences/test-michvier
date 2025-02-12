from parameterized import parameterized, parameterized_class
import unittest
import io
from unittest import mock

import re
import os
import sys

def find_end(inputs, bracket):
    opened_brackets = 0
    for i in range(len(inputs)):
        if inputs[i] == bracket[0]:
            opened_brackets = opened_brackets + 1
        if inputs[i] == bracket[1]:
            if opened_brackets == 1:
                return i
            else:
                opened_brackets = opened_brackets - 1
    return 0

def parse_type(value):
    value = value.strip()
    if value in ['True','False']:
        value = value == 'True'
    elif value[0] == '"' and value[len(value)-1] == '"':
        value = str(value[1:-1])
    else:
        if '.' in value:
            try:
                value = float(value)
            except ValueError:
                value = str(value)
        elif value.isnumeric():
            try:
                value = int(value)
            except ValueError:
                value = str(value)
    return value

def parse_dict(inputs):
    params = {}
    done = False
    while not done:
        if len(inputs) == 0:
            done = True
            break
        k = parse_type(inputs.split(':',1)[0])
        inputs = inputs.split(':',1)[1].strip()
        match inputs[0]:
            case '[':
                idx = find_end(inputs, ('[',']'))
                v = parse_params(inputs[1:idx])
                if idx+2 <= len(inputs):
                    inputs = inputs[idx+2:]
                else:
                    done = True
            case '(':
                idx = find_end(inputs, ('(',')'))
                v = tuple(parse_params(inputs[1:idx]))
                if idx+2 <= len(inputs):
                    inputs = inputs[idx+2:]
                else:
                    done = True
            case '{':
                idx = find_end(inputs, ('{','}'))
                v = parse_dict(inputs[1:idx])
                if idx+2 <= len(inputs):
                    inputs = inputs[idx+2:]
                else:
                    done = True
            case '"':
                if '",' in inputs:
                    v = str(inputs[1:].split('",',1)[0])
                    inputs = inputs.split('",',1)[1]
                else:
                    v = str(inputs[1:].split('"',1)[0])
                    done = True
            case _:
                if ',' in inputs:
                    v = parse_type(inputs.split(',',1)[0])
                    inputs = inputs.split(',',1)[1]
                else:
                    v = parse_type(inputs)
                    done = True
        params[k] = v
    return params

def parse_params(inputs):
    params = []
    done = False
    while not done:
        if len(inputs) == 0:
            done = True
            break
        inputs = inputs.strip()
        match inputs[0]:
            case '[':
                idx = find_end(inputs, ('[',']'))
                value = parse_params(inputs[1:idx])
                if idx+2 <= len(inputs):
                    inputs = inputs[idx+2:]
                else:
                    done = True
            case '(':
                idx = find_end(inputs, ('(',')'))
                value = tuple(parse_params(inputs[1:idx]))
                if idx+2 <= len(inputs):
                    inputs = inputs[idx+2:]
                else:
                    done = True
            case '{':
                idx = find_end(inputs, ('{','}'))
                value = parse_dict(inputs[1:idx])
                if idx+2 <= len(inputs):
                    inputs = inputs[idx+2:]
                else:
                    done = True
            case '"':
                if '",' in inputs:
                    value = str(inputs[1:].split('",',1)[0])
                    inputs = inputs.split('",',1)[1]
                else:
                    value = str(inputs[1:].split('"',1)[0])
                    done = True
            case _:
                if ',' in inputs:
                    value = parse_type(inputs.split(',',1)[0])
                    inputs = inputs.split(',',1)[1]
                else:
                    value = parse_type(inputs)
                    done = True
        params.append(value)
    return params

para_list = []
parse_list = []

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
os.chdir('..')

with open('.test/test_parameters.tsv') as csv:
    for line in csv.readlines()[1:]:
        line_data = line.strip().split('\t')
        if len(line_data[3]) == 0: # handle no given method name -> default to main
            line_data[3] = 'main'
        if len(line_data[4]) == 0: # handle io test inputs (assumed string)
            line_data[4] = []
        else:
            line_data[4] = line_data[4].strip().split(',')
            line_data[4] = [s.strip('') for s in line_data[4]]
            line_data[4] = [s.strip('"') for s in line_data[4]]
        if len(line_data[5]) == 0: # handle io test outputs (assumed string)
            line_data[5] = None
        else:
            line_data[5] = line_data[5].strip('"')
            line_data[5] = line_data[5].strip()
        if len(line_data[6]) == 0: # handle method test parameters
            line_data[6] = None
        else:
            inputs = line_data[6].strip()
            line_data[6] = parse_params(inputs)
        if len(line_data[7]) == 0: # handle method test returns
            line_data[7] = None
        else:
            outputs = line_data[7].strip()
            line_data[7] = parse_params(outputs)
        line_data[11] = float(line_data[11])
        line_data[12] = float(line_data[12])
        para_list.append(tuple(line_data))

with open('.test/test_parse.tsv') as csv:
    for line in csv.readlines()[1:]:
        line_data = line.strip().split('\t')
        line_data[4] = re.sub('"','\'',line_data[4])
        line_data[8] = float(line_data[8])
        line_data[9] = float(line_data[9])
        parse_list.append(tuple(line_data))

class Statistics():
    analytics = []
    report = {}
    points = {}
    total_points = {}

class TestCases(unittest.TestCase):
    @parameterized.expand(para_list, skip_on_empty=True)
    def test_io(self, name, id, class_name, method_name, io_input, io_output, method_params, method_return, succ_msg, err_msg, comp, earnable_points, total_points):
        if class_name not in Statistics.report.keys():
            Statistics.report[class_name] = f'# Task {class_name[-1]}'
        
        if class_name not in Statistics.points.keys():
            Statistics.points[class_name] = 0.0

        if class_name not in Statistics.total_points.keys():
            Statistics.total_points[class_name] = total_points

        if succ_msg != None and succ_msg != '':
            succ_msg = f'\n{succ_msg}\n'

        if err_msg != None and err_msg != '':
            err_msg = f'\n{err_msg}\n'

        try:
            module = __import__(class_name)
            func = getattr(module, method_name)
        except IndentationError:
            Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:0.0')
            raise
        except:
            Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:0.0')
            Statistics.report[class_name] += f'\nTest \'{name}\' failed - {str(0.0)}/{str(total_points)}\nCould not find method {method_name} in class {class_name}. Make sure you typed the name correctly.'
            raise
        
        lines = []
        in_comment = False
        
        try:
            with open(class_name + '.py') as code:
                for line in code.readlines():
                    if re.sub('\s+','',line).startswith(f'"""') or re.sub('\s+','',line).startswith(f'\'\'\''):
                        in_comment = not in_comment
                    if in_comment or re.sub('\s+','',line).startswith('#'):
                        continue
                    if re.sub('\s+','',line).startswith(f'def') and f'{method_name}(' in line:
                        lines.append(line)
                        continue
                    if re.sub('\s+','',line).startswith(f'def') and not f'{method_name}(' in line:
                        break
                    if len(lines) >= 1 and re.sub('\s+','',lines[0]).startswith(f'def') and f'{method_name}(' in lines[0]:
                        lines.append(line)
        except:
            Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:0.0')
            Statistics.report[class_name] += f'\nTest \'{name}\' failed - {str(0.0)}/{str(total_points)}\nCould not find class {class_name}. Make sure you typed the name correctly.'
            raise

        if len(lines) <= 1:
            Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:0.0')
            if '\n' not in Statistics.report[class_name]:
                del Statistics.report[class_name]
            return
        
        with mock.patch('sys.stdout', new=io.StringIO()) as fake_out:
            with mock.patch('builtins.input', side_effect=io_input):
                try:
                    if method_params == None or len(method_params) == 0:
                        actual_return = func()
                    elif len(method_params) == 1:
                        actual_return = func(method_params[0])
                    else:
                        actual_return = func(method_params)
                except IndentationError:
                    Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:0.0')
                    raise
                except:
                    Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:0.0')
                    Statistics.report[class_name] += f'\nTest \'{name}\' failed - {str(0.0)}/{str(total_points)}\nCould not call method {method_name} with the given parameters {str(method_params)}. Make sure the method uses the correct signature.'
                    raise
                actual_output = fake_out.getvalue()
        
        input_string = ''
        output_string = ''
        passed_io = True
        passed_meth = True

        if io_input != None and len(io_input) != 0:
            input_string = input_string + '\nconsole inputs: ' + str(io_input).strip('[').strip(']')

        if method_params != None:
            input_string = input_string + '\nmethod parameters: (' + str(method_params).strip('[').strip(']') + ')'

        if io_output != None:
            io_output = re.sub(';','\n',io_output)
            try:
                self.assertEqual(re.sub('\s+','',io_output).lower(), re.sub('\s+','',actual_output.strip()).lower())
            except AssertionError:
                passed_io = False
                output_string = output_string + '\nTest \'{name}\' failed - {str(0.0)}/{str(total_points)}\nThe console output is not the expected \n\'' + str(io_output) + '\'\nInstead it is \n\'' + actual_output.strip() + '\''

        if method_return != None:
            try:
                self.assertEqual(method_return, actual_return)
            except AssertionError:
                passed_meth = False
                output_string = output_string + '\nTest \'{name}\' failed - {str(0.0)}/{str(total_points)}\nThe method return is not the expected \n\'' + method_return + '\'\nInstead it is \n\'' + actual_return + '\''

        if passed_io and passed_meth:
            Statistics.points[class_name] += round(earnable_points,2)
            Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:{str(round(earnable_points,2))}')
            Statistics.report[class_name] += f'\nTest \'{name}\' passed - {str(round(earnable_points,2))}/{str(total_points)}{input_string}{succ_msg}'
        else:
            Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:0.0')
            Statistics.report[class_name] += f'\nTest \'{name}\' failed - {str(0.0)}/{str(total_points)}{input_string}{output_string}{err_msg}'
            if not passed_io:
                self.assertEqual(re.sub('\s+','',io_output).lower(), re.sub('\s+','',actual_output.strip()).lower())
            else:
                self.assertEqual(method_return, actual_return)

    @parameterized.expand(parse_list, skip_on_empty=True)
    def test_parse(self, name, id, class_name, method_name, value, succ_msg, err_msg, comp, earnable_points, total_points):
        if class_name not in Statistics.report.keys():
            Statistics.report[class_name] = f'# Task {class_name[-1]}'
        
        if class_name not in Statistics.points.keys():
            Statistics.points[class_name] = 0.0

        if class_name not in Statistics.total_points.keys():
            Statistics.total_points[class_name] = total_points

        if succ_msg != None and succ_msg != '':
            succ_msg = f'\n{succ_msg}\n'

        if err_msg != None and err_msg != '':
            err_msg = f'\n{err_msg}\n'

        passed = False

        lines = []
        in_comment = False
        
        try:
            with open(class_name + '.py') as code:
                for line in code.readlines():
                    if re.sub('\s+','',line).startswith(f'"""') or re.sub('\s+','',line).startswith(f'\'\'\''):
                        in_comment = not in_comment
                    if in_comment or re.sub('\s+','',line).startswith('#'):
                        continue
                    if re.sub('\s+','',line).startswith(f'def') and f'{method_name}(' in line:
                        lines.append(line)
                        continue
                    if re.sub('\s+','',line).startswith(f'def') and not f'{method_name}(' in line:
                        break
                    if len(lines) >= 1 and re.sub('\s+','',lines[0]).startswith(f'def') and f'{method_name}(' in lines[0]:
                        lines.append(line)
        except:
            Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:0.0')
            Statistics.report[class_name] += f'\nTest \'{name}\' failed - {str(0.0)}/{str(total_points)}\nCould not find class {class_name}. Make sure you typed the name correctly.'
            raise

        if len(lines) <= 1:
            Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:0.0')
            if '\n' not in Statistics.report[class_name]:
                del Statistics.report[class_name]
            return
        
        try:
            for line in lines:
                if re.sub('\s+','',value).lower() in re.sub('\s+','',re.sub('"','\'',line)).lower():
                    passed = True
                    break
        except:
            Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:0.0')
            Statistics.report[class_name] += f'\nTest \'{name}\' failed - {str(0.0)}/{str(total_points)}\nCould not find class {class_name}. Make sure you typed the name correctly.'
            raise
        
        if passed:
            Statistics.points[class_name] += round(earnable_points,2)
            Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:{str(round(earnable_points,2))}')
            Statistics.report[class_name] += f'\nTest \'{name}\' passed - {str(round(earnable_points,2))}/{str(total_points)}{succ_msg}'
        else:
            Statistics.analytics.append(f'id:{id};test:{name};competence:{comp};method:{class_name}-{method_name};points:0.0')
            Statistics.report[class_name] += f'\nTest \'{name}\' failed - {str(0.0)}/{str(total_points)}{err_msg}'
            self.assertTrue(passed)

    @classmethod
    def tearDownClass(cls):
        for key in Statistics.report.keys():
            print(Statistics.report[key])
            print(f'\nPoints for this task: {Statistics.points[key]}/{Statistics.total_points[key]}\n')
        with open('.test/analytics.csv','a', newline='') as data:
            import csv
            import time
            timestamp = time.ctime(time.time())
            analytics = csv.writer(data, delimiter=',')
            for line in Statistics.analytics:
                vals = [timestamp]
                for pair in line.split(';'):
                    if len(pair.split(':')) == 2:
                        vals.append(pair.split(':')[1])
                    else: vals.append('')
                analytics.writerow(vals)
        print(f'\npoints_total: {sum(Statistics.points.values())}')
