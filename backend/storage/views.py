"""
For shared storage management
"""
import os
import time
import logging
import tarfile
from tempfile import TemporaryFile
import json
import hashlib
from threading import Thread
from django.views import View
from django.http import JsonResponse
from kubernetes import client
from kubernetes.stream import stream
from kubernetes.client.rest import ApiException
from kubernetes.client import CoreV1Api
from api.common import RESPONSE
from api.common import getKubernetesAPIClient
from config import KUBERNETES_NAMESPACE
from storage.models import FileModel, FileStatusCode

LOGGER = logging.getLogger(__name__)


class StorageHandler(View):
    http_method_names = ['get', 'post', 'delete']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_instance = CoreV1Api(getKubernetesAPIClient())

    def get(self, request, **_):
        """
        @api {get} /storage/ Get PVC list
        @apiName GetPVCList
        @apiGroup StorageManager
        @apiVersion 0.1.0
        @apiSuccess {Object} payload Response Object
        @apiSuccess {Number} payload.count Count of total PV claims
        @apiSuccess {Object[]} payload.entry List of PVC
        @apiSuccess {String} payload.entry.name PVC name
        @apiSuccess {String} payload.entry.capacity PVC capacity
        @apiUse APIHeader
        @apiUse Success
        @apiUse ServerError
        @apiUse InvalidRequest
        @apiUse OperationFailed
        @apiUse Unauthorized
        @apiUse PermissionDenied
        """
        try:
            pvc_list = self.api_instance.list_namespaced_persistent_volume_claim(namespace=KUBERNETES_NAMESPACE).items
            payload = {}
            payload['count'] = len(pvc_list)
            payload['entry'] = []
            for pvc in pvc_list:
                payload['entry'].append({'name': pvc.metadata.name, 'capacity': pvc.spec.resources.requests['storage'],
                                         'time': pvc.metadata.creation_timestamp})
            response = RESPONSE.SUCCESS
            response['payload'] = payload
        except Exception:
            response = RESPONSE.SERVER_ERROR
        return JsonResponse(response)

    def post(self, request, **_):
        """
        @api {post} /storage/ Create a PVC
        @apiName CreatePVC
        @apiGroup StorageManager
        @apiVersion 0.1.0
        @apiParamExample {json} Request-Body-Example:
        {
            "name": "new_pvc_name",
            "capacity": "1Gi"
        }
        @apiParam {String} name Name of the PVC
        @apiParam {String} capacity Required capacity for storage
        @apiSuccess {Object} payload Success payload is empty
        @apiUse APIHeader
        @apiUse Success
        @apiUse ServerError
        @apiUse InvalidRequest
        @apiUse OperationFailed
        @apiUse Unauthorized
        @apiUse PermissionDenied
        """
        query = json.loads(request.body)
        # request.encoding = 'utf-8'
        try:
            pvc_name = query.get('name', None)
            pvc_capacity = query.get('capacity', None)
            assert pvc_name is not None
            assert pvc_capacity is not None
        except Exception:
            return JsonResponse(RESPONSE.INVALID_REQUEST)

        # Create specific namespace
        try:
            self.api_instance.create_namespace(client.V1Namespace(api_version="v1", kind="Namespace",
                                                                  metadata=client.V1ObjectMeta(
                                                                      name=KUBERNETES_NAMESPACE,
                                                                      labels={"name": KUBERNETES_NAMESPACE})))
        except Exception:
            # namespaces already exists
            pass

        # Create PVC
        PVC_body = client.V1PersistentVolumeClaim(api_version="v1", kind="PersistentVolumeClaim", \
                                                  metadata=client.V1ObjectMeta(name=pvc_name,
                                                                               namespace=KUBERNETES_NAMESPACE), \
                                                  spec=client.V1PersistentVolumeClaimSpec(
                                                      access_modes=["ReadWriteMany"],
                                                      resources=client.V1ResourceRequirements(
                                                          requests={"storage": pvc_capacity}),
                                                      storage_class_name="csi-cephfs"))
        try:
            self.api_instance.create_namespaced_persistent_volume_claim(namespace=KUBERNETES_NAMESPACE, body=PVC_body)
            response = RESPONSE.SUCCESS
        except Exception:
            response = RESPONSE.OPERATION_FAILED
            response['message'] += " PVC named {} already exists.".format(pvc_name)

        return JsonResponse(response)

    def delete(self, request, **_):
        """
        @api {delete} /storage/ Delete a PV claim
        @apiName DeletePVC
        @apiGroup StorageManager
        @apiVersion 0.1.0
        @apiParamExample {json} Request-Example:
        {
            "name": "pvc_name"
        }
        @apiParam {String} name Name of the PVC to be deleted
        @apiSuccess {Object} payload Success payload is empty
        @apiUse APIHeader
        @apiUse Success
        @apiUse ServerError
        @apiUse InvalidRequest
        @apiUse OperationFailed
        @apiUse Unauthorized
        @apiUse PermissionDenied
        """
        query = json.loads(request.body)
        # query = request.GET
        try:
            pvc_name = query.get('name', None)
            assert pvc_name is not None
        except Exception:
            return JsonResponse(RESPONSE.INVALID_REQUEST)

        try:
            self.api_instance.delete_namespaced_persistent_volume_claim(name=pvc_name, namespace=KUBERNETES_NAMESPACE)
            response = RESPONSE.SUCCESS
        except Exception as e:
            response = RESPONSE.OPERATION_FAILED
            response['message'] += " PVC {} not found.".format(pvc_name)
            response['info'] = str(e)

        return JsonResponse(response)


class StorageFileHandler(View):
    http_method_names = ['post', 'get', 'put']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.save_dir = "storage/data/"
        self.api_instance = CoreV1Api(getKubernetesAPIClient())

    def put(self, request, **_):
        """
        @api {post} /storage/upload_file/ re-upload cached files
        @apiName ReuploadCachedFiles
        @apiGroup StorageManager
        @apiVersion 0.1.0
        @apiSuccess {Object} payload Response payload is empty
        @apiUse APIHeader
        @apiUse Success
        @apiUse ServerError
        @apiUse InvalidRequest
        @apiUse OperationFailed
        @apiUse Unauthorized
        @apiUse PermissionDenied
        """
        self.restart()
        return JsonResponse(RESPONSE.SUCCESS)

    def restart(self):
        """continue uploading when server restarts"""
        file_list = FileModel.objects.all()
        for f in file_list:
            pod_name = "file-upload-pod-" + f.hashid
            if f.status == 0:
                FileModel.objects.filter(hashid=f.hashid).update(status=FileStatusCode.FAILED)
                try:
                    self.api_instance.delete_namespaced_pod(pod_name, KUBERNETES_NAMESPACE)
                except Exception:
                    pass
            elif f.status == 1:
                FileModel.objects.filter(hashid=f.hashid).update(status=FileStatusCode.FAILED)
                try:
                    self.api_instance.delete_namespaced_pod(pod_name, KUBERNETES_NAMESPACE)
                except Exception:
                    pass
            elif f.status == 2 or f.status == 3:
                # cached or uploading
                FileModel.objects.filter(hashid=f.hashid).update(status=FileStatusCode.CACHED)
                uploading = Thread(target=self.uploading, args=(f.filename, f.targetpvc, f.targetpath, f.hashid))
                uploading.start()
            elif f.status == 4:
                try:
                    self.api_instance.delete_namespaced_pod(pod_name, KUBERNETES_NAMESPACE)
                except Exception:
                    pass

    def get(self, request, **_):
        """
        @api {post} /storage/upload_file/ get uploading file list
        @apiName getUploadingFileList
        @apiGroup StorageManager
        @apiVersion 0.1.0
        @apiSuccess {Object} payload Response Object
        @apiSuccess {Number} payload.count Count of total files
        @apiSuccess {Number} payload.page_count Count of total pages
        @apiSuccess {Object[]} payload.entry List of files
        @apiSuccess {String} payload.entry.id File hash ID
        @apiSuccess {String} payload.entry.name Filename
        @apiSuccess {String} payload.entry.pvc Target PVC
        @apiSuccess {String} payload.entry.path Target path
        @apiSuccess {Number} payload.entry.status File uploading status
        @apiUse APIHeader
        @apiUse Success
        @apiUse ServerError
        @apiUse InvalidRequest
        @apiUse OperationFailed
        @apiUse Unauthorized
        @apiUse PermissionDenied
        """
        try:
            page = int(request.GET.get('page', 1))
        except Exception:
            return JsonResponse(RESPONSE.INVALID_REQUEST)
        file_list = FileModel.objects.all().order_by('-uploadtime')
        response = RESPONSE.SUCCESS
        payload = {
            'count': len(file_list),
            'page_count': (len(file_list) + 24) // 25,
            'entry': []
        }

        if page < 1 or page > payload['page_count']:
            if page == 1 and payload['page_count'] == 0:
                pass
            else:
                raise ValueError()
        for f in file_list[25 * (page - 1): 25 * page]:
            payload['entry'].append({'id': f.hashid,
                                     'name': f.filename,
                                     'pvc': f.targetpvc,
                                     'path': f.targetpath,
                                     'status': f.status,
                                     'time': f.uploadtime
                                     })
        response['payload'] = payload
        return JsonResponse(response)

    def post(self, request, **_):
        """
        @api {post} /storage/upload_file/ Upload a file into a pvc storage
        @apiName UploadFile
        @apiGroup StorageManager
        @apiVersion 0.1.0
        @apiParamExample {json} Request-Example:
        {
            "file": [FILE],
            "pvcName": "mypvc",
            "mountPath": "data/"
        }
        @apiParam {String} fileDirectory directory of the file to be uploaded
        @apiParam {String} pvcName name of the target PVC
        @apiParam {String} mountPath target path in storage
        @apiSuccess {Object} payload Success payload is empty
        @apiUse APIHeader
        @apiUse Success
        @apiUse ServerError
        @apiUse InvalidRequest
        @apiUse OperationFailed
        @apiUse Unauthorized
        @apiUse PermissionDenied
        """
        try:
            files = request.FILES.getlist('file[]', None)
            if files is None:
                response = RESPONSE.INVALID_REQUEST
                response['message'] += " File is empty."
                return JsonResponse(response)
            pvc_name = request.POST.get('pvcName', None)
            path = request.POST.get('mountPath', None)
            assert pvc_name is not None
            assert path is not None
        except Exception:
            response = RESPONSE.INVALID_REQUEST
            return JsonResponse(response)
        # check if pvc exists
        try:
            self.api_instance.read_namespaced_persistent_volume_claim_status(name=pvc_name,
                                                                             namespace=KUBERNETES_NAMESPACE)
        except Exception:
            response = RESPONSE.OPERATION_FAILED
            response['message'] += " PVC {} does not exist in namespaced {}".format(pvc_name, KUBERNETES_NAMESPACE)
            return JsonResponse(response)

        # create if namespace does not exist
        try:
            self.api_instance.create_namespace(client.V1Namespace(api_version="v1", kind="Namespace",
                                                                  metadata=client.V1ObjectMeta(
                                                                      name=KUBERNETES_NAMESPACE,
                                                                      labels={"name": KUBERNETES_NAMESPACE})))
        except Exception:
            pass
        for file_upload in files:
            # record file
            uploadtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            LOGGER.info(uploadtime)
            identity = file_upload.name + pvc_name + path + uploadtime
            md = hashlib.md5()
            md.update(identity.encode('utf-8'))
            md = md.hexdigest()
            fileModel = FileModel(hashid=md, filename=file_upload.name, targetpath=path, targetpvc=pvc_name,
                                  status=FileStatusCode.PENDING, uploadtime=uploadtime)
            fileModel.save()

            uploading = Thread(target=self.caching, args=(file_upload, pvc_name, path, md))
            uploading.start()
            FileModel.objects.filter(hashid=md).update(status=FileStatusCode.CACHING)

        response = RESPONSE.SUCCESS
        return JsonResponse(response)

    def caching(self, file_upload, pvc_name, path, md):
        """cache file"""
        # cache file
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        file_save = open(self.save_dir + file_upload.name, 'wb+')
        for chunk in file_upload.chunks():
            file_save.write(chunk)
        file_save.close()
        FileModel.objects.filter(hashid=md).update(status=FileStatusCode.CACHED)
        self.uploading(file_upload.name, pvc_name, path, md)

    def uploading(self, file_name, pvc_name, path, md):
        """a new thread to create pod and upload file"""
        # create pod running a container with image nginx, bound pvc
        volume_name = "file-upload-volume-" + md
        container_name = "file-upload-container-" + md
        pod_name = "file-upload-pod-" + md
        try:
            volume = client.V1Volume(name=volume_name,
                                     persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                         claim_name=pvc_name, read_only=False))
            volume_mount = client.V1VolumeMount(name=volume_name, mount_path='/cephfs-data/')
            container = client.V1Container(name=container_name, image="nginx:1.7.9", image_pull_policy="IfNotPresent",
                                           volume_mounts=[volume_mount])
            pod = client.V1Pod(api_version="v1", kind="Pod",
                               metadata=client.V1ObjectMeta(name=pod_name, namespace=KUBERNETES_NAMESPACE),
                               spec=client.V1PodSpec(containers=[container], volumes=[volume]))
            self.api_instance.create_namespaced_pod(namespace=KUBERNETES_NAMESPACE, body=pod)
        except ApiException as e:
            LOGGER.warning("Kubernetes ApiException %d: %s", e.status, e.reason)
            if e.status != 409:
                return
        except ValueError as e:
            LOGGER.warning(e)
            return
        except Exception as e:
            LOGGER.error(e)

        try:
            while self.api_instance.read_namespaced_pod_status(pod_name,
                                                               KUBERNETES_NAMESPACE).status.phase != "Running":
                time.sleep(1)
        except ApiException as e:
            LOGGER.warning("Kubernetes ApiException %d: %s", e.status, e.reason)
            return
        except ValueError as e:
            LOGGER.warning(e)
            return
        except Exception as e:
            LOGGER.error(e)
            return

        try:
            # create filedir
            exec_command = ['mkdir', '/cephfs-data/' + path]
            resp = stream(self.api_instance.connect_get_namespaced_pod_exec, pod_name, KUBERNETES_NAMESPACE,
                          command=exec_command, \
                          stderr=True, stdin=True, stdout=True, tty=False, _preload_content=False)

            FileModel.objects.filter(hashid=md).update(status=FileStatusCode.UPLOADING)
            exec_command = ['tar', 'xvf', '-', '-C', '/cephfs-data/' + path]
            resp = stream(self.api_instance.connect_get_namespaced_pod_exec, pod_name, KUBERNETES_NAMESPACE,
                          command=exec_command, \
                          stderr=True, stdin=True, stdout=True, tty=False, _preload_content=False)

            with TemporaryFile() as tar_buffer:
                with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                    tar.add(self.save_dir + file_name, arcname=file_name)

                tar_buffer.seek(0)
                commands = []
                commands.append(tar_buffer.read())

                while resp.is_open():
                    resp.update(timeout=1)
                    # if resp.peek_stdout(): print("STDOUT: %s" % resp.read_stdout())
                    # if resp.peek_stderr(): print("STDERR: %s" % resp.read_stderr())
                    if commands:
                        c = commands.pop(0)
                        resp.write_stdin(c.decode())
                    else:
                        break
                resp.close()
        except Exception as e:
            LOGGER.error(e)

        # delete pod when finished
        try:
            self.api_instance.delete_namespaced_pod(pod_name, KUBERNETES_NAMESPACE)
        except Exception:
            pass

        # delete file in memory
        if os.path.exists(self.save_dir + file_name):
            os.remove(self.save_dir + file_name)

        FileModel.objects.filter(hashid=md).update(status=FileStatusCode.SUCCEEDED)
        LOGGER.info("File uploaded successfully.")
