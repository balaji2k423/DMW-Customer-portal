from django.db import models
from django.conf import settings


class DocumentCategory(models.TextChoices):
    COMMERCIALS          = 'commercials',          'Commercials'
    MANUALS              = 'manuals',              'Manuals'
    DRAWINGS             = 'drawings',             'Drawings'
    COMMISSIONING        = 'commissioning',        'Commissioning Reports'
    CERTIFICATES         = 'certificates',         'Certificates'
    OTHER                = 'other',                'Other'


def document_upload_path(instance, filename):
    return f"documents/{instance.project.id}/{instance.category}/{filename}"


class Document(models.Model):

    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        PUBLISHED = 'published', 'Published'
        ARCHIVED  = 'archived',  'Archived'

    project      = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    uploaded_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
    title        = models.CharField(max_length=255)
    description  = models.TextField(blank=True)
    category     = models.CharField(max_length=50, choices=DocumentCategory.choices, default=DocumentCategory.OTHER)
    file         = models.FileField(upload_to=document_upload_path)
    file_size    = models.PositiveBigIntegerField(default=0, help_text='File size in bytes')
    file_type    = models.CharField(max_length=50, blank=True, help_text='e.g. pdf, docx, dwg')
    version      = models.CharField(max_length=20, default='v1.0')
    status       = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    is_public    = models.BooleanField(default=False, help_text='Visible to all project members')
    download_count = models.PositiveIntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.version}) — {self.project.name}"

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            name = self.file.name
            self.file_type = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
        super().save(*args, **kwargs)


class DocumentVersion(models.Model):
    """
    Tracks previous versions when a document is updated.
    The current version always lives on Document.file.
    """
    document    = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='document_versions'
    )
    file        = models.FileField(upload_to='document_versions/')
    version     = models.CharField(max_length=20)
    change_note = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.document.title} — {self.version}"