TWO CHANGES NEEDED in your views.py:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHANGE 1 — Fix dead Groq model in FormaAIConversationView
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FIND:
                model="llama3-8b-8192",

REPLACE WITH:
                model="llama-3.3-70b-versatile",

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHANGE 2 — generate_pdf_status must return the real pdf_url
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your generate_pdf_status view in the pasted file is JUST this:

    @api_view(['GET'])
    @permission_classes([permissions.IsAuthenticated])
    def generate_pdf_status(request, job_id):
        return Response(_get_job(job_id))

REPLACE THE WHOLE FUNCTION with:

    @api_view(['GET'])
    @permission_classes([permissions.IsAuthenticated])
    def generate_pdf_status(request, job_id):
        job_data = _get_job(job_id)
        if not job_data:
            return Response({"status": "not_found"}, status=404)

        pdf_url = job_data.get("pdf_url", "")

        # If stored pdf_url is a raw Cloudinary public_id (not https://), sign it now
        if pdf_url and not pdf_url.startswith("http"):
            try:
                signed_url, _ = _cld_url(pdf_url, resource_type="raw", sign_url=True, secure=True)
                if signed_url:
                    job_data["pdf_url"] = signed_url
            except Exception as e:
                logger.warning(f"Could not sign pdf_url {pdf_url}: {e}")

        # If complete but pdf_url still missing, pull from LeadMagnet record
        if job_data.get("status") == "complete" and not job_data.get("pdf_url"):
            lm_id = job_data.get("lead_magnet_id")
            if lm_id:
                try:
                    lm = LeadMagnet.objects.get(id=lm_id)
                    if lm.pdf_file:
                        public_id = str(lm.pdf_file.name if hasattr(lm.pdf_file, 'name') else lm.pdf_file)
                        if public_id.startswith("http"):
                            job_data["pdf_url"] = public_id
                        else:
                            signed_url, _ = _cld_url(public_id, resource_type="raw", sign_url=True, secure=True)
                            if signed_url:
                                job_data["pdf_url"] = signed_url
                                PDFGenerationJob.objects.filter(job_id=job_id).update(pdf_url=signed_url)
                except LeadMagnet.DoesNotExist:
                    pass

        return Response(job_data)