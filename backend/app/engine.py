import re
TAX={
"Python":["python"],"JavaScript":["javascript","js"],"React":["react","react.js"],"Node.js":["node.js","nodejs","express"],
"FastAPI":["fastapi"],"Flask":["flask"],"REST APIs":["rest api","restful api","api development","api integration"],
"SQL":["sql","mysql","postgresql","sqlite"],"MongoDB":["mongodb"],"Git":["git","github","version control"],
"Docker":["docker","containerization"],"AWS":["aws","amazon web services"],"Machine Learning":["machine learning","ml","scikit-learn"],
"Deep Learning":["deep learning","pytorch","tensorflow"],"NLP":["nlp","natural language processing"],"Data Analysis":["data analysis","pandas","data visualization"],
"Cybersecurity":["cybersecurity","cyber security","penetration testing"],"HTML/CSS":["html","css"],"Tailwind CSS":["tailwind"],
"Problem Solving":["problem solving","data structures","algorithms","dsa"],"Agile":["agile","scrum"],"Testing":["unit testing","pytest","jest","test automation"],
"CI/CD":["ci/cd","continuous integration"],"Cloud Computing":["cloud computing","cloud deployment"],"System Design":["system design","microservices"]}
PROJECTS={
"Python":("Build a Resume Bullet Analyzer","Create a Python CLI that extracts action verbs and outputs a structured JSON summary.",["File handling","Functions","JSON","Unit tests"]),
"REST APIs":("Build a Mini REST API","Create a FastAPI service with CRUD endpoints, validation, status codes and OpenAPI docs.",["FastAPI","Pydantic","HTTP methods","API tests"]),
"SQL":("Build a Query Practice Dashboard","Create a SQLite dataset and write queries covering joins, grouping and aggregation.",["SQLite","JOIN","GROUP BY","Indexes"]),
"React":("Build an Evidence Tracker UI","Build a responsive React interface with reusable components, validation and persistent sample data.",["Components","Hooks","Forms","Responsive CSS"]),
"Machine Learning":("Build a Model Evaluation Notebook","Train a baseline classifier and report precision, recall, F1 and limitations.",["Pandas","Scikit-learn","Metrics","Data leakage"]),
"Git":("Publish a Clean Project Repository","Create a README, meaningful commits, issue checklist and tagged release.",["Git workflow","README","Branches","Release"]),
"Docker":("Containerize a Small API","Write a Dockerfile, build an image and document environment-based configuration.",["Dockerfile","Images","Ports","Environment"]),
"Cybersecurity":("Build a Security Header Auditor","Write a safe HTTP header checker for a domain you own or are authorized to test.",["HTTP headers","HTTPS","Python requests","Responsible testing"]),
"Data Analysis":("Create a Dataset Insight Report","Clean a public dataset, derive three insights and communicate them with a chart.",["Pandas","Cleaning","Statistics","Visualization"])}
QUESTIONS={"Python":["How do you handle exceptions and validate external input?","Explain list vs tuple."],"React":["When would you use useEffect?","How do you manage shared component state?"],"REST APIs":["How do HTTP methods and status codes shape a REST API?","How would you secure an API endpoint?"],"SQL":["Explain INNER JOIN vs LEFT JOIN.","How would you find duplicate records?"],"Machine Learning":["Why split data into train and test sets?","Which metric suits imbalanced classification?"],"Git":["Describe a branching workflow.","How do you resolve a merge conflict?"],"Docker":["Image vs container?","How do you pass configuration to a container?"]}
def skills(text):
    t=text.lower(); out=[]
    for s,aliases in TAX.items():
        if any(re.search(r'(?<![a-z0-9])'+re.escape(a)+r'(?![a-z0-9])',t) for a in aliases):out.append(s)
    return out
def sentences(t):
    return [re.sub(r'\s+',' ',x).strip() for x in re.split(r'(?<=[.!?])\s+|[\n•●]',t) if len(x.strip())>=18]
def sim(a,b):
    stop={"and","the","with","for","from","your","have","using","used","into","this","that","are","was","will","ability","experience"}
    x={w for w in re.findall(r'[a-z0-9+#.]+',a.lower()) if len(w)>2 and w not in stop}; y={w for w in re.findall(r'[a-z0-9+#.]+',b.lower()) if len(w)>2 and w not in stop}
    return len(x&y)/max(1,len(x|y))
def analyse(resume,jd,role):
    req=skills(jd); req=req or skills(resume)[:8]; ss=sentences(resume); items=[]
    for skill in req:
        matches=[]
        for sentence in ss:
            direct=any(a in sentence.lower() for a in TAX.get(skill,[skill.lower()]))
            action=bool(re.search(r'\b(built|developed|implemented|created|deployed|designed|trained|integrated|tested|automated|delivered|secured|optimized)\b',sentence.lower()))
            metric=bool(re.search(r'\b\d+%|\b\d+\s*(users|clients|records|requests|projects)\b',sentence.lower()))
            score=(.52 if direct else 0)+min(.25,sim(skill,sentence)) +(.14 if action else 0)+(.09 if metric else 0)
            if score>.12:matches.append((score,sentence,direct,action,metric))
        matches.sort(reverse=True); top=matches[0] if matches else None
        status="demonstrated" if top and top[0]>=.64 and top[2] else "partial" if top and top[0]>=.28 else "missing"
        items.append({"skill":skill,"status":status,"confidence":round(min(.99,top[0]) if top else 0,2),
          "evidence":[{"snippet":m[1],"signals":[label for label,ok in [("direct skill mention",m[2]),("action verb",m[3]),("measurable outcome",m[4])] if ok],"match":round(min(.99,m[0]),2)} for m in matches[:3]],
          "review_required":status!="demonstrated","interpretation":{"demonstrated":"Direct skill mention supported by an action-oriented resume statement.","partial":"Related evidence was found, but the resume does not yet demonstrate the requirement strongly enough.","missing":"No reliable evidence was found in the supplied resume. This is not proof that you lack the skill."}[status]})
    counts={k:sum(x["status"]==k for x in items) for k in ["demonstrated","partial","missing"]}; n=len(items)
    projects=[]
    for x in [i["skill"] for i in items if i["status"]!="demonstrated"][:5]:
        title,desc,tags=PROJECTS.get(x,(f"Create a proof project for {x}",f"Build a small, reviewable artifact demonstrating {x}. Document the problem, approach, tests and outcome.",["Working demo","README","Tests","Reflection"]))
        projects.append({"skill":x,"title":title,"description":desc,"duration":"2 days","deliverables":tags})
    qs=[{"skill":s,"question":q} for s in req for q in QUESTIONS.get(s,[f"Describe a project where you applied {s}. What did you contribute and how did you validate the result?"])]
    return {"role_title":role,"summary":{"total":n,**counts,"readiness":round((counts["demonstrated"]+.5*counts["partial"])/n*100) if n else 0},"skills":items,"action_plan":projects,"interview_questions":qs[:10],"engine":"Deterministic taxonomy + source-grounded evidence signals","disclaimer":"Not Evidenced means no proof was found in this resume, not that the person lacks the skill. This is decision support, not a hiring decision. Review every evidence anchor."}
