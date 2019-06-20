

def enroll_learners_in_course(course, learners, auto_enroll, ):
    """
    THIS IS A STUB!!!

    adapted from lms/djangoapps/instructor/views/api.py:students_update_enrollment
    """
    results = []

    for learners in learners:
        results.append({
            'learners': learners,
            'result': 'mock',
            })

    # JLB says: "results" is a generic anti-pattern. Here as a temp until we
    # discover what we really need to return
    # can we return just the course enrollments?
    return results
