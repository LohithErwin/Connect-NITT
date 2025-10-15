from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any, Dict
from neo4j import GraphDatabase
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
app = FastAPI(title="Connect-NITT")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
NEO4J_DATABASE = "test"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

class LoginModel(BaseModel):
    email: EmailStr
    password: str
    role: str

class StudentModel(BaseModel):
    roll_number: str
    password: str
    name: str
    phone_number: str
    email: EmailStr
    current_sem: Optional[str] = None
    dob: Optional[str] = None
    address: Optional[str] = None
    current_gpa: Optional[float] = None
    guardian_name: Optional[str] = None
    guardian_contact_number: Optional[str] = None
    pwd: Optional[str] = "no"
    department_id: str
    branch_name: str
    course: str

class AlumniModel(BaseModel):
    alumni_id: str
    password: str
    name: str
    phone_number: str
    email: EmailStr
    pass_out_year: int
    work_experience: Optional[int] = 0
    current_company: Optional[str] = None
    current_role: Optional[str] = None
    department_id: str
    branch_name: str
    course: str

class FacultyModel(BaseModel):
    faculty_id: str
    password: str
    name: str
    phone_number: str
    email: EmailStr
    subjects: Optional[List[str]] = []
    department_id: str

class DepartmentModel(BaseModel):
    DepartmentId: str
    name: str
    number_of_branches: Optional[int] = 0
    branches: Optional[List[str]] = []

class ServiceModel(BaseModel):
    name: str
    description: Optional[str] = ""
    price: float
    provider_email: EmailStr

class BuyServiceModel(BaseModel):
    service_name: str
    buyer_email: EmailStr

class FriendRequestModel(BaseModel):
    from_email: EmailStr
    to_email: EmailStr

class AcceptFriendModel(BaseModel):
    from_email: EmailStr
    to_email: EmailStr

class UnfriendModel(BaseModel):
    user1_email: EmailStr
    user2_email: EmailStr

class LikeServiceModel(BaseModel):
    service_name: str
    user_email: EmailStr

class CommentServiceModel(BaseModel):
    service_name: str
    user_email: EmailStr
    comment_text: str

class DeleteCommentModel(BaseModel):
    service_name: str
    user_email: EmailStr
    comment_id: str

def run_read_query(query: str, params: Dict[str, Any] = None):
    params = params or {}
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(query, params)
        rows = [record.data() for record in result]
    return rows

def run_write_query(query: str, params: Dict[str, Any] = None):
    params = params or {}
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(query, params)

@app.post("/init/create_department")
def create_department(d: DepartmentModel):
    query = """
    MERGE (dept:Department {DepartmentId:$DepartmentId})
    SET dept.name = $name, dept.number_of_branches = $number_of_branches,
    dept.branches = $branches
    RETURN dept
    """
    run_write_query(query, d.dict())
    return {"message": "Department created/updated"}

@app.post("/login")
def login(data: LoginModel):
    label = data.role.capitalize()
    query = f"""
    MATCH (n:{label})
    WHERE n.email = $email AND n.password = $password
    RETURN n.name AS name, labels(n) AS labels, n.email AS email
    """
    res = run_read_query(query, {"email": data.email, "password": data.password})
    if not res:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": f"Welcome {res[0]['name']}", "role": data.role}

@app.post("/add/student")
def add_student(student: StudentModel):
    query = """
    CREATE (s:Student {
        roll_number:$roll_number, password:$password, name:$name,
        phone_number:$phone_number, email:$email, current_sem:$current_sem,
        dob:$dob, address:$address, current_gpa:$current_gpa,
        guardian_name:$guardian_name, guardian_contact_number:$guardian_contact_number,
        pwd:$pwd
    })
    WITH s
    MATCH (d:Department {DepartmentId:$department_id})
    MERGE (s)-[:STUDIES_IN {Branch_name:$branch_name, course:$course}]->(d)
    RETURN s
    """
    params = student.dict()
    params["department_id"] = params.pop("department_id")
    run_write_query(query, params)
    return {"message": "Student added successfully"}

@app.post("/add/alumni")
def add_alumni(a: AlumniModel):
    query = """
    CREATE (a:Alumni {
        alumni_id:$alumni_id, password:$password, name:$name,
        phone_number:$phone_number, email:$email,
        pass_out_year:$pass_out_year, work_experience:$work_experience,
        current_company:$current_company, current_role:$current_role
    })
    WITH a
    MATCH (d:Department {DepartmentId:$department_id})
    MERGE (a)-[:STUDIED_IN {Branch_name:$branch_name, course:$course}]->(d)
    RETURN a
    """
    params = a.dict()
    params["department_id"] = params.pop("department_id")
    run_write_query(query, params)
    return {"message": "Alumni added successfully"}

@app.post("/add/faculty")
def add_faculty(f: FacultyModel):
    query = """
    CREATE (f:Faculty {
        faculty_id:$faculty_id, password:$password, name:$name,
        phone_number:$phone_number, email:$email, subjects:$subjects
    })
    WITH f
    MATCH (d:Department {DepartmentId:$department_id})
    MERGE (f)-[:WORKS_IN]->(d)
    RETURN f
    """
    params = f.dict()
    params["department_id"] = params.pop("department_id")
    run_write_query(query, params)
    return {"message": "Faculty added successfully"}

@app.get("/services/posted/{email}")
def get_posted_services(email: str):
    """Get services posted by a specific user (both used and unused)"""
    query = """
    MATCH (p)-[rel:PROVIDES]->(s:Service_Available)
    WHERE p.email = $email
    OPTIONAL MATCH (buyer)-[used:USED_SERVICE]->(s)
    OPTIONAL MATCH (u)-[like:LIKES]->(s)
    WITH s, p,
         count(DISTINCT like) as like_count,
         collect(DISTINCT {email: buyer.email, name: buyer.name, used_at: used.used_at}) as used_by_list
    RETURN s{.*, 
             provider: {name: p.name, email: p.email},
             like_count: like_count,
             used_by: [u IN used_by_list WHERE u.email IS NOT NULL | u],
             is_used: size([u IN used_by_list WHERE u.email IS NOT NULL | u]) > 0
    } AS service
    ORDER BY s.name
    """
    rows = run_read_query(query, {"email": email})
    return rows

@app.post("/add/service")
def add_service(s: ServiceModel):
    query = """
    MATCH (p) WHERE p.email = $provider_email
    CREATE (service:Service_Available {name:$name, description:$description, price:$price})
    MERGE (p)-[r:PROVIDES]->(service)
    SET r.provided_at = datetime(), r.provider_email = $provider_email
    RETURN service
    """
    rows = run_read_query(query, s.dict())
    if not rows:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Service added"}

@app.get("/students/{email}")
def get_student_detail(email: str):
    query = """
    MATCH (s:Student {email:$email})-[r:STUDIES_IN]->(d:Department)
    RETURN s{.*, Branch:r.Branch_name, Department:d.name} AS student
    """
    rows = run_read_query(query, {"email": email})
    if not rows:
        raise HTTPException(status_code=404, detail="Student not found")
    return rows

@app.get("/alumni/{email}")
def get_alumni_detail(email: str):
    query = """
    MATCH (a:Alumni {email:$email})-[r:STUDIED_IN]->(d:Department)
    RETURN a{.*, Branch:r.Branch_name, Department:d.name} AS alumni
    """
    rows = run_read_query(query, {"email": email})
    if not rows:
        raise HTTPException(status_code=404, detail="Alumni not found")
    return rows

@app.get("/faculty/{email}")
def get_faculty_detail(email: str):
    query = """
    MATCH (f:Faculty {email:$email})-[r:WORKS_IN]->(d:Department)
    RETURN f{.*, Department:d.name} AS faculty
    """
    rows = run_read_query(query, {"email": email})
    if not rows:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return rows


@app.get("/students")
def get_students(branch: Optional[str] = None, department: Optional[str] = None):
    query = """
    MATCH (s:Student)-[r:STUDIES_IN]->(d:Department)
    WHERE ($branch IS NULL OR r.Branch_name = $branch)
    AND ($department IS NULL OR d.DepartmentId = $department)
    RETURN s{.*, Branch:r.Branch_name, Department:d.name} AS student
    ORDER BY s.name
    """
    rows = run_read_query(query, {"branch": branch, "department": department})
    return rows

@app.get("/alumni")
def get_alumni(branch: Optional[str] = None, department: Optional[str] = None, pass_out: Optional[int] = None):
    query = """
    MATCH (a:Alumni)-[r:STUDIED_IN]->(d:Department)
    WHERE ($branch IS NULL OR r.Branch_name = $branch)
    AND ($department IS NULL OR d.DepartmentId = $department)
    AND ($pass_out IS NULL OR a.pass_out_year = $pass_out)
    RETURN a{.*, Branch:r.Branch_name, Department:d.name} AS alumni
    ORDER BY a.name
    """
    rows = run_read_query(query, {"branch": branch, "department": department, "pass_out": pass_out})
    return rows

@app.get("/faculty")
def get_faculty(department: Optional[str] = None):
    query = """
    MATCH (f:Faculty)-[:WORKS_IN]->(d:Department)
    WHERE ($department IS NULL OR d.DepartmentId = $department)
    RETURN f{.*, Department:d.name} AS faculty
    ORDER BY f.name
    """
    rows = run_read_query(query, {"department": department})
    return rows

@app.get("/services")
def get_services():
    """Get all services that have NOT been used by anyone"""
    query = """
    MATCH (s:Service_Available)
    WHERE NOT EXISTS((s)<-[:USED_SERVICE]-())
    OPTIONAL MATCH (p)-[rel:PROVIDES]->(s)
    OPTIONAL MATCH (u)-[like:LIKES]->(s)
    OPTIONAL MATCH (s)-[c:HAS_COMMENT]->(comment:Comment)
    OPTIONAL MATCH (commenter) WHERE commenter.email = comment.user_email
    WITH s, 
         collect(DISTINCT {name: p.name, email: p.email, labels: labels(p)}) as providers,
         count(DISTINCT like) as like_count,
         collect(DISTINCT u.email) as liked_by,
         collect(DISTINCT {
             id: comment.id,
             text: comment.text,
             user_email: comment.user_email,
             user_name: commenter.name,
             created_at: comment.created_at
         }) as comments
    RETURN s{.*, 
             providers: providers, 
             like_count: like_count,
             liked_by: liked_by,
             comments: [c IN comments WHERE c.id IS NOT NULL | c]
    } AS service
    ORDER BY s.name
    """
    rows = run_read_query(query)
    return rows

# @app.get("/services")
# def get_services():
#     query = """
#     MATCH (s:Service_Available)
#     OPTIONAL MATCH (p)-[rel:PROVIDES]->(s)
#     OPTIONAL MATCH (u)-[like:LIKES]->(s)
#     OPTIONAL MATCH (buyer)-[used:USED_SERVICE]->(s)
#     OPTIONAL MATCH (s)-[c:HAS_COMMENT]->(comment:Comment)
#     OPTIONAL MATCH (commenter) WHERE commenter.email = comment.user_email
#     WITH s, 
#          collect(DISTINCT {name: p.name, email: p.email, labels: labels(p)}) as providers,
#          count(DISTINCT like) as like_count,
#          collect(DISTINCT u.email) as liked_by,
#          collect(DISTINCT buyer.email) as used_by,
#          collect(DISTINCT {
#              id: comment.id,
#              text: comment.text,
#              user_email: comment.user_email,
#              user_name: commenter.name,
#              created_at: comment.created_at
#          }) as comments
#     RETURN s{.*, 
#              providers: providers, 
#              like_count: like_count,
#              liked_by: liked_by,
#              used_by: [u IN used_by WHERE u IS NOT NULL | u],
#              comments: [c IN comments WHERE c.id IS NOT NULL | c]
#     } AS service
#     ORDER BY s.name
#     """
#     rows = run_read_query(query)
#     return rows

@app.get("/services/my/{email}")
def get_my_services(email: str):
    """Get services used by the user."""
    query = """
    MATCH (u)-[used:USED_SERVICE]->(s:Service_Available)
    WHERE u.email = $email
    OPTIONAL MATCH (p)-[rel:PROVIDES]->(s)
    RETURN s{.*, 
             provider: {name: p.name, email: p.email},
             used_at: used.used_at
    } AS service
    ORDER BY used.used_at DESC
    """
    rows = run_read_query(query, {"email": email})
    return rows

@app.get("/services/{service_name}")
def get_service_details(service_name: str):
    query = """
    MATCH (s:Service_Available {name:$service_name})
    OPTIONAL MATCH (p)-[rel:PROVIDES]->(s)
    OPTIONAL MATCH (u)-[like:LIKES]->(s)
    OPTIONAL MATCH (s)-[c:HAS_COMMENT]->(comment:Comment)
    OPTIONAL MATCH (commenter) WHERE commenter.email = comment.user_email
    WITH s, 
         collect(DISTINCT {name: p.name, email: p.email, labels: labels(p)}) as providers,
         count(DISTINCT like) as like_count,
         collect(DISTINCT {email: u.email, name: u.name}) as liked_by,
         collect(DISTINCT {
             id: comment.id,
             text: comment.text,
             user_email: comment.user_email,
             user_name: commenter.name,
             created_at: comment.created_at
         }) as comments
    RETURN s{.*, 
             providers: providers, 
             like_count: like_count,
             liked_by: [l IN liked_by WHERE l.email IS NOT NULL | l],
             comments: [c IN comments WHERE c.id IS NOT NULL | c]
    } AS service
    """
    rows = run_read_query(query, {"service_name": service_name})
    if not rows:
        raise HTTPException(status_code=404, detail="Service not found")
    return rows[0]

@app.post("/buy_service")
def buy_service(buy: BuyServiceModel):
    query = """
    MATCH (s:Service_Available {name:$service_name})
    MATCH (p) WHERE p.email = $buyer_email
    MERGE (p)-[rel:USED_SERVICE]->(s)
    SET rel.Used_by = $buyer_email, rel.used_at = datetime()
    RETURN p, s
    """
    rows = run_read_query(query, buy.dict())
    if not rows:
        raise HTTPException(status_code=404, detail="Service or buyer not found")
    return {"message": "Service registered as used successfully"}

@app.post("/services/like")
def like_service(req: LikeServiceModel):
    check_query = """
    MATCH (u)-[like:LIKES]->(s:Service_Available {name:$service_name})
    WHERE u.email = $user_email
    RETURN like
    """
    existing = run_read_query(check_query, req.dict())
    
    if existing:
        unlike_query = """
        MATCH (u)-[like:LIKES]->(s:Service_Available {name:$service_name})
        WHERE u.email = $user_email
        DELETE like
        RETURN u, s
        """
        run_write_query(unlike_query, req.dict())
        return {"message": "Service unliked", "liked": False}
    else:
        like_query = """
        MATCH (s:Service_Available {name:$service_name})
        MATCH (u) WHERE u.email = $user_email
        MERGE (u)-[like:LIKES]->(s)
        SET like.liked_at = datetime()
        RETURN u, s
        """
        rows = run_read_query(like_query, req.dict())
        if not rows:
            raise HTTPException(status_code=404, detail="Service or user not found")
        return {"message": "Service liked", "liked": True}

@app.post("/services/comment")
def comment_on_service(req: CommentServiceModel):
    """Add a comment to a service."""
    query = """
    MATCH (s:Service_Available {name:$service_name})
    MATCH (u) WHERE u.email = $user_email
    CREATE (comment:Comment {
        id: randomUUID(),
        text: $comment_text,
        user_email: $user_email,
        created_at: datetime()
    })
    MERGE (s)-[:HAS_COMMENT]->(comment)
    RETURN comment, u.name as user_name
    """
    rows = run_read_query(query, req.dict())
    if not rows:
        raise HTTPException(status_code=404, detail="Service or user not found")
    
    return {
        "message": "Comment added successfully",
        "comment": {
            "id": rows[0]["comment"]["id"],
            "text": rows[0]["comment"]["text"],
            "user_email": rows[0]["comment"]["user_email"],
            "user_name": rows[0]["user_name"],
            "created_at": str(rows[0]["comment"]["created_at"])
        }
    }

@app.delete("/services/comment")
def delete_comment(req: DeleteCommentModel):
    """Delete a comment (only by the comment author)."""
    query = """
    MATCH (s:Service_Available {name:$service_name})-[:HAS_COMMENT]->(comment:Comment {id:$comment_id})
    WHERE comment.user_email = $user_email
    DETACH DELETE comment
    RETURN count(comment) as deleted
    """
    rows = run_read_query(query, req.dict())
    if not rows or rows[0]["deleted"] == 0:
        raise HTTPException(status_code=404, detail="Comment not found or unauthorized")
    return {"message": "Comment deleted successfully"}

@app.get("/services/{service_name}/comments")
def get_service_comments(service_name: str):
    """Get all comments for a specific service."""
    query = """
    MATCH (s:Service_Available {name:$service_name})-[:HAS_COMMENT]->(comment:Comment)
    OPTIONAL MATCH (u) WHERE u.email = comment.user_email
    RETURN comment{.*, user_name: u.name} as comment
    ORDER BY comment.created_at DESC
    """
    rows = run_read_query(query, {"service_name": service_name})
    return rows

@app.post("/friends/request")
def send_friend_request(req: FriendRequestModel):
    """Send a friend request from one user to another."""
    check_query = """
    MATCH (u1)-[r:FRIENDS_WITH]-(u2)
    WHERE u1.email = $from_email AND u2.email = $to_email
    RETURN r
    """
    existing = run_read_query(check_query, req.dict())
    if existing:
        raise HTTPException(status_code=400, detail="Already friends")

    pending_query = """
    MATCH (u1)-[r:FRIEND_REQUEST]->(u2)
    WHERE u1.email = $from_email AND u2.email = $to_email
    RETURN r
    """
    pending = run_read_query(pending_query, req.dict())
    if pending:
        raise HTTPException(status_code=400, detail="Friend request already sent")
    
    query = """
    MATCH (sender) WHERE sender.email = $from_email
    MATCH (receiver) WHERE receiver.email = $to_email
    CREATE (sender)-[req:FRIEND_REQUEST {
        sent_at: datetime(),
        status: 'pending'
    }]->(receiver)
    RETURN sender.name as sender_name, receiver.name as receiver_name
    """
    rows = run_read_query(query, req.dict())
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "message": f"Friend request sent from {rows[0]['sender_name']} to {rows[0]['receiver_name']}"
    }

@app.post("/friends/accept")
def accept_friend_request(req: AcceptFriendModel):
    """Accept a friend request and create bidirectional friendship."""
    check_query = """
    MATCH (sender)-[req:FRIEND_REQUEST]->(receiver)
    WHERE sender.email = $from_email AND receiver.email = $to_email
    RETURN req
    """
    existing = run_read_query(check_query, req.dict())
    if not existing:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    query = """
    MATCH (sender)-[req:FRIEND_REQUEST]->(receiver)
    WHERE sender.email = $from_email AND receiver.email = $to_email
    DELETE req
    WITH sender, receiver
    CREATE (sender)-[:FRIENDS_WITH {since: datetime()}]->(receiver)
    CREATE (receiver)-[:FRIENDS_WITH {since: datetime()}]->(sender)
    RETURN sender.name as sender_name, receiver.name as receiver_name
    """
    rows = run_read_query(query, req.dict())
    
    return {
        "message": f"{rows[0]['receiver_name']} and {rows[0]['sender_name']} are now friends"
    }

@app.post("/friends/reject")
def reject_friend_request(req: AcceptFriendModel):
    """Reject a friend request."""
    query = """
    MATCH (sender)-[req:FRIEND_REQUEST]->(receiver)
    WHERE sender.email = $from_email AND receiver.email = $to_email
    DELETE req
    RETURN count(req) as deleted
    """
    rows = run_read_query(query, req.dict())
    if not rows or rows[0]["deleted"] == 0:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    return {"message": "Friend request rejected"}

@app.post("/friends/unfriend")
def unfriend(req: UnfriendModel):
    """Remove friendship between two users."""
    query = """
    MATCH (u1)-[r:FRIENDS_WITH]-(u2)
    WHERE (u1.email = $user1_email AND u2.email = $user2_email)
    OR (u1.email = $user2_email AND u2.email = $user1_email)
    DELETE r
    RETURN count(r) as deleted
    """
    rows = run_read_query(query, req.dict())
    if not rows or rows[0]["deleted"] == 0:
        raise HTTPException(status_code=404, detail="Friendship not found")
    
    return {"message": "Unfriended successfully"}

@app.get("/friends/{email}")
def get_friends(email: str):
    """Get all friends of a user."""
    query = """
    MATCH (u)-[r:FRIENDS_WITH]->(friend)
    WHERE u.email = $email
    RETURN friend{.name, .email, labels: labels(friend), since: r.since} as friend
    ORDER BY friend.name
    """
    rows = run_read_query(query, {"email": email})
    return {"friends": rows}

@app.get("/friends/requests/received/{email}")
def get_received_friend_requests(email: str):
    """Get all pending friend requests received by a user."""
    query = """
    MATCH (sender)-[req:FRIEND_REQUEST]->(receiver)
    WHERE receiver.email = $email AND req.status = 'pending'
    RETURN sender{.name, .email, labels: labels(sender), sent_at: req.sent_at} as request
    ORDER BY req.sent_at DESC
    """
    rows = run_read_query(query, {"email": email})
    return {"requests": rows}

@app.delete("/services/{name}")
def delete_service(name: str):
    """Delete a service provided by a user."""
    query = """
    MATCH (s:Service_Available {name:$name})
    DETACH DELETE s
    RETURN count(s) as deleted
    """
    rows = run_read_query(query, {"name": name})
    return {"message": "Service deleted successfully"}


@app.get("/friends/requests/sent/{email}")
def get_sent_friend_requests(email: str):
    """Get all pending friend requests sent by a user."""
    query = """
    MATCH (sender)-[req:FRIEND_REQUEST]->(receiver)
    WHERE sender.email = $email AND req.status = 'pending'
    RETURN receiver{.name, .email, labels: labels(receiver), sent_at: req.sent_at} as request
    ORDER BY req.sent_at DESC
    """
    rows = run_read_query(query, {"email": email})
    return {"requests": rows}

@app.get("/friends/suggestions/{email}")
def get_friend_suggestions(email: str, limit: int = 10):
    """Get friend suggestions - all users (students, alumni, faculty) who are not friends."""
    query = """
    MATCH (u) WHERE u.email = $email
    
    MATCH (suggestion)
    WHERE suggestion.email <> $email
    AND NOT (u)-[:FRIENDS_WITH]-(suggestion)
    AND NOT (u)-[:FRIEND_REQUEST]-(suggestion)
    AND (suggestion:Student OR suggestion:Alumni OR suggestion:Faculty)
    
    OPTIONAL MATCH (u)-[:FRIENDS_WITH]->(friend)-[:FRIENDS_WITH]->(suggestion)
    WITH suggestion, count(DISTINCT friend) as mutual_count
    
    OPTIONAL MATCH (u)-[r1:STUDIES_IN|STUDIED_IN|WORKS_IN]->(d:Department)<-[r2:STUDIES_IN|STUDIED_IN|WORKS_IN]-(suggestion)
    WITH suggestion, mutual_count,
         CASE WHEN d IS NOT NULL THEN 1 ELSE 0 END as same_dept
    
    RETURN DISTINCT suggestion{.name, .email, labels: labels(suggestion)} as suggestion,
           mutual_count,
           same_dept
    ORDER BY mutual_count DESC, same_dept DESC
    LIMIT $limit
    """
    rows = run_read_query(query, {"email": email, "limit": limit})
    return {"suggestions": rows}

@app.get("/friends/network/{email}")
def get_friend_network(email: str, depth: int = 2):
    query = """
    MATCH path = (u)-[:FRIENDS_WITH*1..%d]-(friend)
    WHERE u.email = $email
    WITH DISTINCT friend
    MATCH (friend)-[r:FRIENDS_WITH]-(connected)
    RETURN DISTINCT friend{.name, .email, labels: labels(friend)} as person,
           collect(DISTINCT connected{.name, .email}) as connections
    LIMIT 50
    """ % depth
    rows = run_read_query(query, {"email": email})
    return {"network": rows}

@app.get("/departments")
def get_departments():
    query = "MATCH (d:Department) RETURN d{.*} AS department"
    return run_read_query(query)

@app.get("/")
def root():
    return {"message": "Connect-NITT FastAPI backend is running with social features"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)