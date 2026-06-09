package controllers

import (
	"context"
	"fmt"
	"os"
	"strconv"
	"time"

	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
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

type ConformanceCheckReconciler struct {
	client.Client
	Scheme    *runtime.Scheme
	Recorder  record.EventRecorder
	Scheduler *internal.Scheduler
	Runner    *internal.JobRunner
}

func (r *ConformanceCheckReconciler) Reconcile(ctx context.Context, req reconcile.Request) (reconcile.Result, error) {
	logger := log.FromContext(ctx)

	check := &validationv1alpha1.ConformanceCheck{}
	if err := r.Get(ctx, req.NamespacedName, check); err != nil {
		if errors.IsNotFound(err) {
			return reconcile.Result{}, nil
		}
		return reconcile.Result{}, err
	}

	if check.Status.Phase == "" {
		check.Status.Phase = validationv1alpha1.PhasePending
	}

	switch check.Status.Phase {
	case validationv1alpha1.PhasePending:
		if !r.Scheduler.TryAcquire() {
			logger.Info("concurrency limit reached, requeueing", "max", r.Scheduler.MaxConcurrent())
			return reconcile.Result{RequeueAfter: 5 * time.Second}, nil
		}

		check.Status.Phase = validationv1alpha1.PhaseRunning
		check.Status.LastRun = &metav1.Time{Time: time.Now()}
		if err := r.Status().Update(ctx, check); err != nil {
			r.Scheduler.Release()
			return reconcile.Result{}, err
		}
		r.Recorder.Event(check, corev1.EventTypeNormal, "ValidationStarted",
			fmt.Sprintf("Check %s started against %s/%s", check.Name, check.Spec.TargetRef.Kind, check.Spec.TargetRef.Name))

		specRef := check.Spec.SpecRef
		if specRef == "" {
			specRef = "petstore-spec"
		}

		if err := r.Runner.CreateValidateJob(ctx, check.Name, check.Namespace,
			check.Spec.TargetRef.Name, check.Spec.TargetRef.Port, specRef,
			check.Spec.DeviceTargets, check.Spec.VisualConfig); err != nil {
			r.Scheduler.Release()
			check.Status.Phase = validationv1alpha1.PhaseError
			_ = r.Status().Update(ctx, check)
			r.Recorder.Event(check, corev1.EventTypeWarning, "ValidationFailed",
				fmt.Sprintf("Failed to create Job: %v", err))
			return reconcile.Result{}, err
		}

		return reconcile.Result{RequeueAfter: 10 * time.Second}, nil

	case validationv1alpha1.PhaseRunning:
		job := &batchv1.Job{}
		err := r.Get(ctx, types.NamespacedName{
			Name:      fmt.Sprintf("validate-%s", check.Name),
			Namespace: check.Namespace,
		}, job)
		if err != nil {
			if errors.IsNotFound(err) {
				return reconcile.Result{RequeueAfter: 10 * time.Second}, nil
			}
			return reconcile.Result{}, err
		}

		for _, c := range job.Status.Conditions {
			if c.Type == batchv1.JobComplete && c.Status == corev1.ConditionTrue {
				check.Status.Phase = validationv1alpha1.PhasePass
				check.Status.Result = &validationv1alpha1.CheckResult{
					Passed:  true,
					Summary: "All gates passed",
				}
				r.Recorder.Event(check, corev1.EventTypeNormal, "ValidationPassed",
					fmt.Sprintf("Check %s passed", check.Name))
				r.Scheduler.Release()
				return reconcile.Result{}, r.Status().Update(ctx, check)
			}
			if c.Type == batchv1.JobFailed && c.Status == corev1.ConditionTrue {
				check.Status.Phase = validationv1alpha1.PhaseFail
				check.Status.Result = &validationv1alpha1.CheckResult{
					Passed:  false,
					Summary: fmt.Sprintf("Job failed: %s", c.Reason),
				}
				r.Recorder.Event(check, corev1.EventTypeWarning, "ValidationFailed",
					fmt.Sprintf("Check %s failed: %s", check.Name, c.Reason))
				r.Scheduler.Release()
				return reconcile.Result{}, r.Status().Update(ctx, check)
			}
		}

		return reconcile.Result{RequeueAfter: 10 * time.Second}, nil

	case validationv1alpha1.PhasePass, validationv1alpha1.PhaseFail, validationv1alpha1.PhaseError:
		return reconcile.Result{}, nil
	}

	return reconcile.Result{}, nil
}

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
