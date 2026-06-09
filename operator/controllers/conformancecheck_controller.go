package controllers

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
	"time"

	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/record"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"
	"sigs.k8s.io/controller-runtime/pkg/reconcile"

	validationv1alpha1 "github.com/cherenkov-ai/operator/api/v1alpha1"
	"github.com/cherenkov-ai/operator/internal"
	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

const (
	defaultRequeueAfter = 30 * time.Second
)

// ConformanceCheckReconciler reconciles a ConformanceCheck object.
type ConformanceCheckReconciler struct {
	client.Client
	Scheme     *runtime.Scheme
	Recorder   record.EventRecorder
	Scheduler  *internal.Scheduler
	Runner     *internal.JobRunner
	KubeClient kubernetes.Interface
}

// Reconcile fetches the ConformanceCheck, lists existing Jobs, creates one if none
// exists, updates status from Job phase, and requeues after 30 seconds.
func (r *ConformanceCheckReconciler) Reconcile(ctx context.Context, req reconcile.Request) (reconcile.Result, error) {
	logger := log.FromContext(ctx)

	// F3: Fetch the ConformanceCheck resource.
	cc := &validationv1alpha1.ConformanceCheck{}
	if err := r.Get(ctx, req.NamespacedName, cc); err != nil {
		if errors.IsNotFound(err) {
			return reconcile.Result{}, nil
		}
		return reconcile.Result{}, err
	}

	// F3: List existing Jobs with label "conformancecheck": cc.Name.
	jobList := &batchv1.JobList{}
	if err := r.List(ctx, jobList,
		client.InNamespace(cc.Namespace),
		client.MatchingLabels{"conformancecheck": cc.Name},
	); err != nil {
		return reconcile.Result{}, err
	}

	// F3: Create a Job if none exists.
	if len(jobList.Items) == 0 {
		logger.Info("creating Job for ConformanceCheck", "name", cc.Name)
		job := r.buildJob(cc)
		if err := r.Create(ctx, job); err != nil {
			if !errors.IsAlreadyExists(err) {
				return reconcile.Result{}, err
			}
		}
		r.Recorder.Event(cc, corev1.EventTypeNormal, "JobCreated",
			fmt.Sprintf("Created Job %s-job for ConformanceCheck %s", cc.Name, cc.Name))
		return reconcile.Result{RequeueAfter: defaultRequeueAfter}, nil
	}

	// F3: Update status from Job phase.
	job := &jobList.Items[0]
	if err := r.updateStatus(ctx, cc, job); err != nil {
		return reconcile.Result{}, err
	}

	// F3: Requeue after 30 seconds.
	return reconcile.Result{RequeueAfter: defaultRequeueAfter}, nil
}

// buildJob constructs a Kubernetes Job for the given ConformanceCheck (F4).
// - Name: {cc.Name}-job
// - Label: conformancecheck: cc.Name
// - RestartPolicy: Never
// - Image: cherenkov/cherenkov:latest
// - Command: ["cherenkov", "validate"] (uses env vars from #388)
// - Env: CHERENKOV_SPEC_URL, CHERENKOV_TARGET_URL, optionally CHERENKOV_DEVICE_TARGETS, CHERENKOV_VLM_TIER
func (r *ConformanceCheckReconciler) buildJob(cc *validationv1alpha1.ConformanceCheck) *batchv1.Job {
	// Issue #388: build env vars from spec fields.
	env := []corev1.EnvVar{
		{Name: "CHERENKOV_SPEC_URL", Value: cc.Spec.SpecURL},
		{Name: "CHERENKOV_TARGET_URL", Value: cc.Spec.TargetURL},
	}
	if len(cc.Spec.DeviceTargets) > 0 {
		deviceJSON, _ := json.Marshal(cc.Spec.DeviceTargets)
		env = append(env, corev1.EnvVar{
			Name:  "CHERENKOV_DEVICE_TARGETS",
			Value: string(deviceJSON),
		})
	}
	if cc.Spec.VisualConfig != nil {
		env = append(env, corev1.EnvVar{
			Name:  "CHERENKOV_VLM_TIER",
			Value: cc.Spec.VisualConfig.VLMTier,
		})
	}

	return &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%s-job", cc.Name),
			Namespace: cc.Namespace,
			Labels: map[string]string{
				"conformancecheck": cc.Name,
			},
			OwnerReferences: []metav1.OwnerReference{
				*metav1.NewControllerRef(cc, validationv1alpha1.GroupVersion.WithKind("ConformanceCheck")),
			},
		},
		Spec: batchv1.JobSpec{
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						"conformancecheck": cc.Name,
						"job-name":         fmt.Sprintf("%s-job", cc.Name),
					},
				},
				Spec: corev1.PodSpec{
					RestartPolicy: corev1.RestartPolicyNever,
					Containers: []corev1.Container{
						{
							Name:    "cherenkov",
							Image:   "cherenkov/cherenkov:latest",
							Command: []string{"cherenkov", "validate"},
							Env:     env,
						},
					},
				},
			},
		},
	}
}

// updateStatus lists pods by job-name label, gets pod logs, parses results,
// updates cc.Status.Results, and calls r.Status().Update(ctx, cc) (F5).
func (r *ConformanceCheckReconciler) updateStatus(ctx context.Context, cc *validationv1alpha1.ConformanceCheck, job *batchv1.Job) error {
	// Determine phase from Job conditions.
	phase := validationv1alpha1.PhasePending
	for _, c := range job.Status.Conditions {
		if c.Type == batchv1.JobComplete && c.Status == corev1.ConditionTrue {
			phase = validationv1alpha1.PhasePass
		} else if c.Type == batchv1.JobFailed && c.Status == corev1.ConditionTrue {
			phase = validationv1alpha1.PhaseFail
		}
	}
	if phase == validationv1alpha1.PhasePending && job.Status.Active > 0 {
		phase = validationv1alpha1.PhaseRunning
	}
	cc.Status.Phase = phase

	// F5: List pods by job-name label.
	podList := &corev1.PodList{}
	if err := r.List(ctx, podList,
		client.InNamespace(cc.Namespace),
		client.MatchingLabels{"job-name": job.Name},
	); err != nil {
		return err
	}

	// F5: Get pod logs and parse results.
	var results []validationv1alpha1.TestResult
	for i := range podList.Items {
		pod := &podList.Items[i]
		if pod.Status.Phase == corev1.PodSucceeded || pod.Status.Phase == corev1.PodFailed {
			logs, err := r.getPodLogs(ctx, pod.Namespace, pod.Name)
			if err == nil {
				parsed := parseResults(logs)
				results = append(results, parsed...)
			}
		}
	}

	// F5: Update cc.Status.Results.
	if len(results) > 0 {
		cc.Status.Results = results
	}

	// F5: Call r.Status().Update(ctx, cc).
	return r.Status().Update(ctx, cc)
}

// getPodLogs retrieves logs from a pod using the Kubernetes pod log API (F5).
func (r *ConformanceCheckReconciler) getPodLogs(ctx context.Context, namespace, podName string) (string, error) {
	if r.KubeClient == nil {
		return "", fmt.Errorf("KubeClient not initialized")
	}
	req := r.KubeClient.CoreV1().Pods(namespace).GetLogs(podName, &corev1.PodLogOptions{})
	stream, err := req.Stream(ctx)
	if err != nil {
		return "", err
	}
	defer stream.Close()
	buf := new(bytes.Buffer)
	if _, err := io.Copy(buf, stream); err != nil {
		return "", err
	}
	return buf.String(), nil
}

// parseResults parses test results from pod log output.
// Expects JSON lines of the form: {"endpoint":"/foo","method":"GET","status":"pass",...}
func parseResults(logs string) []validationv1alpha1.TestResult {
	var results []validationv1alpha1.TestResult
	for _, line := range strings.Split(logs, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		var r validationv1alpha1.TestResult
		if err := json.Unmarshal([]byte(line), &r); err == nil && r.Endpoint != "" {
			results = append(results, r)
		}
	}
	return results
}

// SetupWithManager sets up the controller with the Manager.
func (r *ConformanceCheckReconciler) SetupWithManager(mgr ctrl.Manager) error {
	maxStr := os.Getenv("MAX_CONCURRENT_LLM_TASKS")
	maxTasks := int32(2)
	if v, err := strconv.Atoi(maxStr); err == nil && v > 0 {
		maxTasks = int32(v)
	}

	r.Scheduler = internal.NewScheduler(maxTasks)
	r.Runner = internal.NewJobRunner(mgr.GetClient())

	return ctrl.NewControllerManagedBy(mgr).
		For(&validationv1alpha1.ConformanceCheck{}).
		Owns(&batchv1.Job{}).
		Named("conformancecheck").
		Complete(r)
}
