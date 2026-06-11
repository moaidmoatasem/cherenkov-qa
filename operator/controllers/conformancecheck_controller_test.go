package controllers

import (
	"context"
	"testing"
	"time"

	validationv1alpha1 "github.com/cherenkov-ai/operator/api/v1alpha1"
	batchv1 "k8s.io/api/batch/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	"k8s.io/client-go/tools/record"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
)

func TestReconcileFinalizer(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = clientgoscheme.AddToScheme(scheme)
	_ = validationv1alpha1.AddToScheme(scheme)
	_ = batchv1.AddToScheme(scheme)

	ctx := context.Background()

	t.Run("Add finalizer to new ConformanceCheck", func(t *testing.T) {
		cc := &validationv1alpha1.ConformanceCheck{
			ObjectMeta: metav1.ObjectMeta{
				Name:      "test-check",
				Namespace: "default",
			},
			Spec: validationv1alpha1.ConformanceCheckSpec{
				SpecURL:   "http://example.com/spec.json",
				TargetURL: "http://example.com/api",
			},
		}

		fakeClient := fake.NewClientBuilder().WithScheme(scheme).WithObjects(cc).WithStatusSubresource(cc).Build()
		recorder := record.NewFakeRecorder(10)

		reconciler := &ConformanceCheckReconciler{
			Client:   fakeClient,
			Scheme:   scheme,
			Recorder: recorder,
		}

		req := ctrl.Request{
			NamespacedName: types.NamespacedName{
				Name:      "test-check",
				Namespace: "default",
			},
		}

		_, err := reconciler.Reconcile(ctx, req)
		if err != nil {
			t.Fatalf("unexpected error during reconcile: %v", err)
		}

		// Verify finalizer was added
		updatedCC := &validationv1alpha1.ConformanceCheck{}
		err = fakeClient.Get(ctx, req.NamespacedName, updatedCC)
		if err != nil {
			t.Fatalf("failed to fetch updated ConformanceCheck: %v", err)
		}

		found := false
		for _, f := range updatedCC.Finalizers {
			if f == cleanupFinalizer {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("expected finalizer %q to be added, but got %v", cleanupFinalizer, updatedCC.Finalizers)
		}
	})

	t.Run("Gracefully delete ConformanceCheck and Job", func(t *testing.T) {
		now := metav1.NewTime(time.Now())
		cc := &validationv1alpha1.ConformanceCheck{
			ObjectMeta: metav1.ObjectMeta{
				Name:              "test-delete",
				Namespace:         "default",
				DeletionTimestamp: &now,
				Finalizers:        []string{cleanupFinalizer},
			},
			Spec: validationv1alpha1.ConformanceCheckSpec{
				SpecURL:   "http://example.com/spec.json",
				TargetURL: "http://example.com/api",
			},
		}

		job := &batchv1.Job{
			ObjectMeta: metav1.ObjectMeta{
				Name:      "test-delete-job",
				Namespace: "default",
				Labels: map[string]string{
					"conformancecheck": "test-delete",
				},
			},
		}

		fakeClient := fake.NewClientBuilder().WithScheme(scheme).WithObjects(cc, job).WithStatusSubresource(cc).Build()
		recorder := record.NewFakeRecorder(10)

		reconciler := &ConformanceCheckReconciler{
			Client:   fakeClient,
			Scheme:   scheme,
			Recorder: recorder,
		}

		req := ctrl.Request{
			NamespacedName: types.NamespacedName{
				Name:      "test-delete",
				Namespace: "default",
			},
		}

		// First reconciliation: should trigger deletion of job and requeue
		res, err := reconciler.Reconcile(ctx, req)
		if err != nil {
			t.Fatalf("unexpected error during first delete reconcile: %v", err)
		}
		if res.RequeueAfter != 2*time.Second {
			t.Errorf("expected requeue after 2s, got %v", res)
		}

		var remainingJobs batchv1.JobList
		_ = fakeClient.List(ctx, &remainingJobs)
		t.Logf("Jobs after first reconcile: %d", len(remainingJobs.Items))
		for _, j := range remainingJobs.Items {
			t.Logf("Remaining Job: %s", j.Name)
		}

		// Verify status phase updated to Terminating
		updatedCC := &validationv1alpha1.ConformanceCheck{}
		_ = fakeClient.Get(ctx, req.NamespacedName, updatedCC)
		if updatedCC.Status.Phase != "Terminating" {
			t.Errorf("expected phase to be Terminating, got %s", updatedCC.Status.Phase)
		}

		// Second reconciliation: Job is already gone in fake client, finalizer should be removed
		_, err = reconciler.Reconcile(ctx, req)
		if err != nil {
			t.Fatalf("unexpected error during second delete reconcile: %v", err)
		}

		// Verify finalizer was removed (which deletes the ConformanceCheck since DeletionTimestamp is set)
		err = fakeClient.Get(ctx, req.NamespacedName, updatedCC)
		if err == nil {
			for _, f := range updatedCC.Finalizers {
				if f == cleanupFinalizer {
					t.Errorf("expected finalizer %q to be removed, but it was found", cleanupFinalizer)
				}
			}
		} else if !errors.IsNotFound(err) {
			t.Fatalf("unexpected error checking deleted ConformanceCheck: %v", err)
		}
	})
}
