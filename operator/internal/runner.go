package internal

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"

	validationv1alpha1 "github.com/cherenkov-ai/operator/api/v1alpha1"
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

func (r *JobRunner) CreateValidateJob(
	ctx context.Context,
	name, namespace, targetService string,
	targetPort int32,
	specRef string,
	deviceTargets []validationv1alpha1.DeviceTarget,
	visualConfig *validationv1alpha1.VisualConfig,
) error {
	env := []corev1.EnvVar{
		{Name: "OLLAMA_HOST", Value: "http://ollama:11434"},
	}

	// Issue #388: pass CHERENKOV_DEVICE_TARGETS as a JSON-encoded array.
	if len(deviceTargets) > 0 {
		deviceJSON, _ := json.Marshal(deviceTargets)
		env = append(env, corev1.EnvVar{
			Name:  "CHERENKOV_DEVICE_TARGETS",
			Value: string(deviceJSON),
		})
	}

	// Issue #388: pass CHERENKOV_VLM_TIER.
	if visualConfig != nil && visualConfig.VLMTier != "" {
		env = append(env, corev1.EnvVar{
			Name:  "CHERENKOV_VLM_TIER",
			Value: visualConfig.VLMTier,
		})
	}

	// Legacy per-device env vars (kept for backward compatibility).
	for i, dt := range deviceTargets {
		prefix := fmt.Sprintf("DEVICE_TARGET_%d_", i)
		env = append(env,
			corev1.EnvVar{Name: prefix + "PLATFORM", Value: dt.Platform},
		)
		if dt.OSVersion != "" {
			env = append(env, corev1.EnvVar{Name: prefix + "OS_VERSION", Value: dt.OSVersion})
		}
		if dt.DeviceName != "" {
			env = append(env, corev1.EnvVar{Name: prefix + "DEVICE_NAME", Value: dt.DeviceName})
		}
		if dt.Browser != "" {
			env = append(env, corev1.EnvVar{Name: prefix + "BROWSER", Value: dt.Browser})
		}
		if dt.ViewportSize != nil {
			env = append(env,
				corev1.EnvVar{Name: prefix + "VIEWPORT_WIDTH", Value: strconv.Itoa(dt.ViewportSize.Width)},
				corev1.EnvVar{Name: prefix + "VIEWPORT_HEIGHT", Value: strconv.Itoa(dt.ViewportSize.Height)},
			)
		}
	}

	if visualConfig != nil {
		env = append(env,
			corev1.EnvVar{Name: "VISUAL_ENABLED", Value: strconv.FormatBool(visualConfig.Enabled)},
		)
		if visualConfig.VLMProvider != "" {
			env = append(env, corev1.EnvVar{Name: "VISUAL_VLM_PROVIDER", Value: visualConfig.VLMProvider})
		}
		if visualConfig.DiffMethod != "" {
			env = append(env, corev1.EnvVar{Name: "VISUAL_DIFF_METHOD", Value: visualConfig.DiffMethod})
		}
	}

	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("validate-%s", name),
			Namespace: namespace,
			Labels: map[string]string{
				"cherenkov.io/check": name,
				"conformancecheck":   name,
			},
		},
		Spec: batchv1.JobSpec{
			BackoffLimit:            int32Ptr(2),
			TTLSecondsAfterFinished: int32Ptr(3600),
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						"cherenkov.io/check": name,
						"conformancecheck":   name,
						"job-name":           fmt.Sprintf("validate-%s", name),
					},
				},
				Spec: corev1.PodSpec{
					RestartPolicy: corev1.RestartPolicyNever,
					Containers: []corev1.Container{
						{
							Name:            "engine",
							Image:           "cherenkov/cherenkov:latest",
							ImagePullPolicy: corev1.PullIfNotPresent,
							Command:         []string{"cherenkov", "validate"},
							Env:             env,
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
