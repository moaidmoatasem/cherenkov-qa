package internal

import (
	"context"
	"fmt"

	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

type JobRunner struct {
	client client.Client
}

func NewJobRunner(c client.Client) *JobRunner {
	return &JobRunner{client: c}
}

func (r *JobRunner) CreateValidateJob(ctx context.Context, name, namespace, targetService string, targetPort int32, specRef string, deviceTarget string) error {
	envVars := []corev1.EnvVar{
		{Name: "OLLAMA_HOST", Value: "http://ollama:11434"},
	}
	if deviceTarget != "" {
		envVars = append(envVars, corev1.EnvVar{Name: "CHERENKOV_DEVICE_TARGET", Value: deviceTarget})
	}

	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("validate-%s", name),
			Namespace: namespace,
			Labels: map[string]string{
				"cherenkov.io/check": name,
			},
		},
		Spec: batchv1.JobSpec{
			BackoffLimit:            int32Ptr(2),
			TTLSecondsAfterFinished: int32Ptr(3600),
			Template: corev1.PodTemplateSpec{
				Spec: corev1.PodSpec{
					RestartPolicy: corev1.RestartPolicyNever,
					Containers: []corev1.Container{
						{
							Name:  "engine",
							Image: "cherenkov-engine:latest",
							ImagePullPolicy: corev1.PullIfNotPresent,
							Env: envVars,
							Args: []string{
								"--spec", "/spec/petstore.json",
								"--target", fmt.Sprintf("http://%s:%d", targetService, targetPort),
								"--output", "json",
							},
							VolumeMounts: []corev1.VolumeMount{
								{Name: "spec", MountPath: "/spec", ReadOnly: true},
							},
						},
					},
					Volumes: []corev1.Volume{
						{
							Name: "spec",
							VolumeSource: corev1.VolumeSource{
								ConfigMap: &corev1.ConfigMapVolumeSource{
									LocalObjectReference: corev1.LocalObjectReference{Name: specRef},
								},
							},
						},
					},
				},
			},
		},
	}

	return r.client.Create(ctx, job)
}

func (r *JobRunner) DeleteValidateJob(ctx context.Context, name, namespace string) error {
	job := &batchv1.Job{}
	err := r.client.Get(ctx, types.NamespacedName{Name: fmt.Sprintf("validate-%s", name), Namespace: namespace}, job)
	if err != nil {
		return client.IgnoreNotFound(err)
	}
	return r.client.Delete(ctx, job)
}

func int32Ptr(i int32) *int32 { return &i }
