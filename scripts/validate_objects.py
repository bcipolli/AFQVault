from django.forms.models import model_to_dict

from afqvault.apps.afqmaps.forms import EditAFQMapForm
from afqvault.apps.afqmaps.models import AFQMap

count = AFQMap.objects.count()
for i, image in enumerate(AFQMap.objects.all()):
    print "Fixing AFQMap %d (%d/%d)" % (image.pk, i + 1, count)
    form = EditAFQMapForm(model_to_dict(image), instance=image, user=image.collection.owner)
    image.is_valid = form.is_valid()
    image.save()
