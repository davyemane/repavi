from django.shortcuts import render

def csrf_failure(request, reason=""):
    return render(request, "csrf_failure.html", status=403, context={"reason": reason})