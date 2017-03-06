import os
import shutil
import tempfile
import urllib
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from nidmfsl.fsl_exporter.fsl_exporter import FSLtoNIDMExporter

from afqvault.apps.afqmaps.forms import NIDMResultsForm
from afqvault.apps.afqmaps.models import Collection,User
from .utils import clearDB


class FeatDirectoryTest(TestCase):

    def setUp(self):
        testpath = os.path.join(os.path.abspath(os.path.dirname(__file__)),'test_data','feat')
        testdata_repo = 'https://github.com/AFQVault/afqvault_data/blob/master/FEAT_testdata/'

        self.testfiles = {
            'ds105.feat.zip': {
                'fileuri':'ds105.feat.zip?raw=true',
                'num_afqmaps':2,
                'export_dir':'ds105.feat/cope1.feat/nidm',
                'ttl_fsize': 30000,
                'map_types': ['T','Z'],
                'names':['Statistic Map: group mean', 'Z-Statistic Map: group mean'],

            },

            'ds017A.zip': {
                'fileuri':'ds017A.zip?raw=true',
                'num_afqmaps':2,
                'export_dir': 'ds017A/group/model001/task001/cope001.gfeat/cope1.feat/nidm',
                'ttl_fsize': 68026,
                'map_types': ['T','Z'],
                'names':['Statistic Map: group mean', 'Z-Statistic Map: group mean'],
            },
        }

        self.tmpdir = tempfile.mkdtemp()
        self.user = User.objects.create_user('NeuroGuy')
        self.user.save()
        self.client = Client()
        self.client.login(username=self.user)
        self.coll = Collection(owner=self.user, name="Test Collection")
        self.coll.save()

        # FEAT test data is large so it lives in the external data repo
        for fname, info in self.testfiles.items():
            self.testfiles[fname]['file'] = os.path.join(testpath,fname)
            if not os.path.exists(self.testfiles[fname]['file']):
                print '\ndownloading test data {}'.format(fname)
                furl = '{0}{1}'.format(testdata_repo, info['fileuri'])
                try:
                    urllib.urlretrieve(furl, self.testfiles[fname]['file'])
                except:
                    os.remove(os.path.join(testpath,fname))
                    raise

            self.testfiles[fname]['sourcedir'] = self.testfiles[fname]['file'][:-4]
            self.testfiles[fname]['dir'] = os.path.join(self.tmpdir,fname[:-4])

            if not os.path.exists(self.testfiles[fname]['sourcedir']):
                fh = open(os.path.join(testpath,fname), 'rb')
                z = zipfile.ZipFile(fh)
                for name in [v for v in z.namelist() if not v.startswith('.') and
                             '/.files' not in v]:
                    outpath = self.testfiles[fname]['sourcedir']
                    z.extract(name, outpath)
                fh.close()

            shutil.copytree(self.testfiles[fname]['sourcedir'], self.testfiles[fname]['dir'])

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        clearDB()
