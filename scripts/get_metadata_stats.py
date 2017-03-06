from afqvault.apps.afqmaps.models import Collection, AFQMap,\
    BaseAFQMap
from django.db.models import Q
total_collection = Collection.objects.all().count()

for field in Collection._meta.fields:
    null_kwargs = {field.name + "__isnull":True}
    empty_string_kwargs = {field.name + "__exact":''}
    if field.empty_strings_allowed:
        count_not_empty = Collection.objects.filter(~Q(**null_kwargs) & ~Q(**empty_string_kwargs)).count()
    else:
        count_not_empty = Collection.objects.filter(~Q(**null_kwargs)).count()
    perc_not_empty = float(count_not_empty)/float(total_collection)*100.0
    print '%s, "%s", "%s", %.4g%%, %d'%(field.name, field.verbose_name, field.help_text, perc_not_empty, count_not_empty)


total_collection = AFQMap.objects.all().count()

for field in set(AFQMap._meta.fields).union(BaseAFQMap._meta.fields):
    null_kwargs = {field.name + "__isnull":True}
    empty_string_kwargs = {field.name + "__exact":''}
    if field.empty_strings_allowed:
        count_not_empty = AFQMap.objects.filter(~Q(**null_kwargs) & ~Q(**empty_string_kwargs)).count()
    else:
        count_not_empty = AFQMap.objects.filter(~Q(**null_kwargs)).count()
    perc_not_empty = float(count_not_empty)/float(total_collection)*100.0
    print '%s, "%s", "%s", %.4g%%, %d'%(field.name, field.verbose_name, field.help_text, perc_not_empty, count_not_empty)