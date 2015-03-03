
from django.conf.urls import patterns, url

from doc.db.urlhelpers import DB_REGEX

from doc.trips.views import *
from doc.trips.views import TripLeaderIndexView

# goal:
# url(CREATE_REGEX, view.as_view(), name=view_name(view))

# OR:


def view_name(view):

    suffix = None
    if isinstance(view, CreateView):
        suffix = 'create'
    # ...

    return '{}_{}'.format(model_reference_name(view.model), suffix)
    
    
trip_urlpatterns = patterns('', 
    url(DB_REGEX['LIST'], ScheduledTripListView.as_view(), name='scheduledtrip_index'),
    url(DB_REGEX['CREATE'], ScheduledTripCreateView.as_view(), name='scheduledtrip_create'),
    url(DB_REGEX['DETAIL'], ScheduledTripDetailView.as_view(), name='scheduledtrip_detail'),                            
    url(DB_REGEX['UPDATE'], ScheduledTripUpdateView.as_view(), name='scheduledtrip_update'),
    url(DB_REGEX['DELETE'], ScheduledTripDeleteView.as_view(), name='scheduledtrip_delete'),                            
)

template_urlpatterns = patterns('',
    TripTemplateListView.urlpattern(),
    url(DB_REGEX['LIST'], TripTemplateListView.as_view(), name='triptemplate_index'),
    TripTemplateCreateView.urlpattern(),                            
    TripTemplateDetailView.urlpattern(),                            
    TripTemplateUpdateView.urlpattern(),                            
    TripTemplateDeleteView.urlpattern(),                        
)                                

triptype_urlpatterns = patterns('',
    url(DB_REGEX['LIST'], TripTypeListView.as_view(), name='triptype_index'),                
    TripTypeCreateView.urlpattern(),                            
    TripTypeDetailView.urlpattern(),                            
    TripTypeUpdateView.urlpattern(),                            
    TripTypeDeleteView.urlpattern(),                        
)                                

campsite_urlpatterns = patterns('',
    url(DB_REGEX['LIST'], CampsiteListView.as_view(), name='campsite_index'),
    CampsiteCreateView.urlpattern(),     
    CampsiteDetailView.urlpattern(),                        
    CampsiteUpdateView.urlpattern(),                            
    CampsiteDeleteView.urlpattern(),                        
)                                

section_urlpatterns = patterns('',
    url(DB_REGEX['LIST'], SectionListView.as_view(), name='section_index'),
    SectionCreateView.urlpattern(),                        
    SectionDetailView.urlpattern(),                           
    SectionUpdateView.urlpattern(),                            
    SectionDeleteView.urlpattern(),                        
)                                

leader_urlpatterns = patterns(
    '', 
    url(r'^$', TripLeaderIndexView.as_view(), name='leader_index'),
    url(r'^assign/(?P<trip>[0-9]+)$', AssignTripLeaderView.as_view(), name='assign_leader'),
    url(r'^assign/post/(?P<leader_pk>[0-9]+)$', 
        UpdateLeaderWithAssignedTrip.as_view(), name='assign_leader_to_trip'),
    url(r'^remove/(?P<leader_pk>[0-9]+)$', 
        RemoveAssignedTrip.as_view(), name='remove_leader_from_trip'),
)
                              

