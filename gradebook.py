import requests, json, sys, datetime, smtplib
from gradebookConfig import *
from contextlib import redirect_stdout
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def getStudentOutcomes(courseNumber, user): #takes in the Canvas course number and student ID number as a string and returns an Outcomes JSON for all assessed standards for that student
    #print("Requesting Outcomes for user #: " + str(user))
    myRequest = 'https://ncssm.instructure.com/api/v1/courses/' + str(courseNumber) + \
                '/outcome_results?user_ids[]=' + str(user) + '&per_page=' + PAGES + '&access_token=' + TOKEN

    return requests.get(myRequest).json()

def getAssignmentName(listOfAssignments, assignmentNumber): # takes in Assignments JSON and assignment number as a string
    name = next((item for item in listOfAssignments if item['id'] == assignmentNumber))
    
    return name['name']

def getAssignmentDate(listOfAssignments, assignmentNumber):
    date = next((item for item in listOfAssignments if item['id'] == assignmentNumber))

    if date['due_at'] is None:
        return '00000000'
    else:
        return date['due_at']

def getAssignments(courseNumber):
    print("Requesting list of assignments...")
    myRequest = 'https://ncssm.instructure.com/api/v1/courses/' + str(courseNumber) + \
                '/assignments/?per_page=' + PAGES + '&access_token=' + TOKEN

    return requests.get(myRequest).json()

def stripAssignment(name): # removes the preceding 'assignment_' that comes in an Outcome JSON alignment
    return name[11:]

def getStudentDictionary(courseNumber):
    print("Requesting Student Info...")
    myRequest = 'https://ncssm.instructure.com/api/v1/courses/' + str(courseNumber) + \
                '/users?enrollment_type[]=student&enrollment_state[]=active&per_page=' + PAGES + '&access_token=' + TOKEN
    
    return requests.get(myRequest).json()

def getStandardName(standardId, listOfAssignments, assignmentNumber):
    assignment = next((item for item in listOfAssignments if item['id'] == assignmentNumber))
    name = next((item for item in assignment['rubric'] if item['outcome_id'] == standardId))
    
    return name['description']

def createStudentList(courseNumber, listOfUsers, listOfAssignments):
    theList = []
    print("Creating the list of users")
    for i in range(len(listOfUsers)):
        print('*',end='')
        theList.append( { 'id' : int(listOfUsers[i]['id']), 'name' : listOfUsers[i]['name'], 'scores' : [] } )
    print('')

    print("Populating the scores")
    for i in theList:
        print('*',end='')
        rawOutcomes = getStudentOutcomes(courseNumber,i['id'])
        scoresList = []
        for j in rawOutcomes['outcome_results']:
            if not (j['score'] is None):
                i['scores'].append({'assignment_id' : j['links']['alignment'], 'assignment_name' : getAssignmentName(listOfAssignments, int(stripAssignment(j['links']['alignment']))), 'due_date' : getAssignmentDate(listOfAssignments, int(stripAssignment(j['links']['alignment']))), 'standard_id' : j['links']['learning_outcome'], 'standard_name' : getStandardName( int(j['links']['learning_outcome']), listOfAssignments, int(stripAssignment(j['links']['alignment']))), 'score' : j['score'] })
    print('')
    return theList

def detailedStudentReport(theList, studentID):
    student = next((item for item in theList if item['id'] == studentID))
    print(student['name'])
    print('----------------')
    for i in range(len(student['scores'])):
        info = 'Standard: ' + student['scores'][i]['standard_name'] + \
                   ' Assignment: ' + student['scores'][i]['assignment_name'] + \
                   ' Time: ' + student['scores'][i]['due_date'] + \
                   ' Score: ' + str(student['scores'][i]['score'])
        print(info)
    return 

def gradeLookup(MP, A, C):
    if not (isinstance(MP,float) and isinstance(A, float) and isinstance(C,float)):
        return 'NA'
    
    scores = [MP, A, C]
    lowest = min(scores)

    if lowest == 2.0:
        return 'A+'
    elif lowest >= 1.8:
        return 'A'
    elif lowest >= 1.7:
        return 'A-'
    elif lowest >= 1.6:
        return 'B+'
    elif lowest >= 1.5:
        return 'B'
    elif lowest >= 1.4:
        return 'B-'
    elif lowest >= 1.2:
        return 'C+'    
    elif lowest >= 1.1:
        return 'C'
    elif lowest >= 1.0:
        return 'C-'
    else:
        return 'D'
        
def summaryStudentReport(theList, studentID, reportType):
    student = next((item for item in theList if item['id'] == studentID))
    student['scores'] = sorted(student['scores'], key=lambda k: k['due_date'])
    print(student['name'])
    print('----------------')

    ######################################
    mpLevels = {}
    for i in student['scores']:
        if standardType1 in i['standard_name']:
            mpLevels[i['standard_name']] = i['score']

    count = 0
    blanks = 0
    for k in mpLevels.keys():
        if isinstance(mpLevels[k], int) or isinstance(mpLevels[k], float):
            count += mpLevels[k]
        else:
            blanks += 1
    if len(mpLevels)-blanks != 0:
        mpLvlAvg = float(count/(len(mpLevels)-blanks))
    else:
        mpLvlAvg = 0

    ####################################### 
    aLevels = {}
    for i in student['scores']:
        if standardType2 in i['standard_name']:
            aLevels[i['standard_name']] = i['score']

    count = 0
    blanks = 0
    for k in aLevels.keys():
        if isinstance(aLevels[k], int) or isinstance(aLevels[k], float):
            count += aLevels[k]
        else:
            blanks += 1
    if len(aLevels)-blanks != 0:
        aLvlAvg = float(count/(len(aLevels)-blanks))
    else:
        aLvlAvg = 0
    #######################################    
    cLevels = {}
    for i in student['scores']:
        if standardType3 in i['standard_name']:
            cLevels[i['standard_name']] = i['score']
    
    count = 0
    blanks = 0
    for k in cLevels.keys():
        if isinstance(cLevels[k], int) or isinstance(cLevels[k], float):
            count += cLevels[k]
        else:
            blanks += 1
    if len(cLevels)-blanks != 0:
        cLvlAvg = float(count/(len(cLevels)-blanks))
    else:
        cLvlAvg = 0
    #######################################

    print('MP Average: {0:.4f} A Average: {1:.4f} C Average: {2:.4f}'.format(mpLvlAvg, aLvlAvg, cLvlAvg))
    print('Course Grade: ', gradeLookup(mpLvlAvg, aLvlAvg, cLvlAvg))
    print('') 
    print("MP-Levels")
    print("--------")
    
    for key, value in sorted(mpLevels.items()):
        print('{}: {}'.format(key, value))

    print('')
    print("A-Levels")
    print("--------")
    for key, value in sorted(aLevels.items()):
        print('{}: {}'.format(key, value))   

    print('')
    print("C-Levels")
    print("--------")
    for key, value in sorted(cLevels.items()):
        print('{}: {}'.format(key, value))

    student['scores'] = sorted(student['scores'], key=lambda k: k['due_date'])
    print('')
    print('All Scores')
    print('----------')
    print('Standard\tScore\tAssignment\t\t\tDate\n')
    for i in range(len(student['scores'])):
        print('{}\t{}\t{}\t\t{}'.format(student['scores'][i]['standard_name'].ljust(10),student['scores'][i]['score'],student['scores'][i]['assignment_name'].ljust(18),student['scores'][i]['due_date']))

    if reportType == 's' or reportType =='S':
        print('page-break')
    return

def menu(myStudents, myInformation):
    choice = ''
    print('\n ___________ _____   _____               _      _                 _    \n/  ___| ___ \  __ \ |  __ \             | |    | |               | |   \n\ `--.| |_/ / |  \/ | |  \/_ __ __ _  __| | ___| |__   ___   ___ | | __\n `--. \ ___ \ | __  | | __| \'__/ _` |/ _` |/ _ \ \'_ \ / _ \ / _ \| |/ /\n/\__/ / |_/ / |_\ \ | |_\ \ | | (_| | (_| |  __/ |_) | (_) | (_) |   < \n\____/\____/ \____/  \____/_|  \__,_|\__,_|\___|_.__/ \___/ \___/|_|\_\\')
    print('v 1.1.0 - January 19, 2017\n\n')
    print('Course #: ', myCourse)
    print('[S] Save Progress Reports (gradeReport-YYYY-MM-DD-hh-mm-ss.txt)\n[E] E-mail Progress Reports\n[X] Exit')
    choice = input('What would you like to do? ')

    if choice == 's' or choice == 'S':
        writeFileReport(myStudents, myInformation, choice)
        menu(myStudents, myInformation)
           
    elif choice == 'x' or choice == 'X':
        print('Quitting')

    elif choice == 'e' or choice == 'E':
        generateEmailReport(myStudents, myInformation, choice)
        menu(myStudents, myInformation)

    else:
        menu(myStudents, myInformation)
           
    return


def writeFileReport(myStudents, myInformation, choice):
    with open('gradeReport-'+ str(datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")) + '.txt', 'a+') as f:
       with redirect_stdout(f):
         for i in myStudents:
           summaryStudentReport(myInformation, int(i['id']), choice)       
    return

def sendEmailReport(address, report):
    fromaddr = emailAddress
    toaddr = address
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = courseName + ' Grade Report (' + str(datetime.datetime.now().strftime("%Y-%m-%d")) + ')'

    body = report
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, emailPassword)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()

    return

def generateEmailReport(myStudents, myInformation, choice):
    for i in myStudents:

        with open('emailReport.txt', 'w+') as f:
           with redirect_stdout(f):
             summaryStudentReport(myInformation, int(i['id']), choice)

        with open('emailReport.txt', 'r') as report:
            grades = report.read()

        sendEmailReport(str(i['login_id']), grades) 

    return

def main():
    myStudents = getStudentDictionary(myCourse) #creates students JSON
    myAssignments = getAssignments(myCourse)    #create assignment JSON (big!)
    myInformation = createStudentList(myCourse, myStudents, myAssignments)

    menu(myStudents,myInformation)

    return

main()
