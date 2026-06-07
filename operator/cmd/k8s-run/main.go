package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/spf13/cobra"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"sigs.k8s.io/controller-runtime/pkg/client"

	validationv1alpha1 "github.com/cherenkov-ai/operator/api/v1alpha1"
	_ "k8s.io/client-go/plugin/pkg/client/auth"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
)

var scheme = runtime.NewScheme()

func init() {
	_ = clientgoscheme.AddToScheme(scheme)
	_ = validationv1alpha1.AddToScheme(scheme)
}

type RunOptions struct {
	Spec      string
	Target    string
	Namespace string
	Port      int32
	Timeout   time.Duration
}

var runOpts RunOptions

func main() {
	cmd := &cobra.Command{
		Use:   "k8s-run",
		Short: "Run a ConformanceCheck on a K8s cluster",
		RunE:  runCheck,
	}

	cmd.Flags().StringVarP(&runOpts.Spec, "spec", "s", "", "OpenAPI spec file or ConfigMap name")
	cmd.Flags().StringVarP(&runOpts.Target, "target", "t", "", "Target service (svc:port)")
	cmd.Flags().StringVarP(&runOpts.Namespace, "namespace", "n", "cherenkov", "K8s namespace")
	cmd.Flags().Int32VarP(&runOpts.Port, "port", "p", 4010, "Target port")
	cmd.Flags().DurationVarP(&runOpts.Timeout, "timeout", "T", 5*time.Minute, "Maximum wait time")

	_ = cmd.MarkFlagRequired("spec")
	_ = cmd.MarkFlagRequired("target")

	if err := cmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func runCheck(cmd *cobra.Command, args []string) error {
	config, err := getConfig()
	if err != nil {
		return fmt.Errorf("get kubernetes config: %w", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return fmt.Errorf("create kubernetes client: %w", err)
	}

	c, err := client.New(config, client.Options{Scheme: scheme})
	if err != nil {
		return fmt.Errorf("create controller-runtime client: %w", err)
	}

	check := &validationv1alpha1.ConformanceCheck{
		ObjectMeta: metav1.ObjectMeta{
			GenerateName: "cli-check-",
			Namespace:    runOpts.Namespace,
		},
		Spec: validationv1alpha1.ConformanceCheckSpec{
			TargetRef: validationv1alpha1.TargetRef{
				APIVersion: "v1",
				Kind:       "Service",
				Name:       runOpts.Target,
				Namespace:  runOpts.Namespace,
				Port:       runOpts.Port,
			},
			SpecRef: runOpts.Spec,
		},
	}

	if err := c.Create(cmd.Context(), check); err != nil {
		return fmt.Errorf("create ConformanceCheck: %w", err)
	}

	fmt.Printf("Created ConformanceCheck %s/%s\n", check.Namespace, check.Name)

	ctx, cancel := context.WithTimeout(cmd.Context(), runOpts.Timeout)
	defer cancel()

	pollInterval := 2 * time.Second
	var lastPhase validationv1alpha1.ConformancePhase

	if err := wait.PollUntilContextTimeout(ctx, pollInterval, runOpts.Timeout, true, func(ctx context.Context) (done bool, err error) {
		updated := &validationv1alpha1.ConformanceCheck{}
		if err := c.Get(ctx, types.NamespacedName{Name: check.Name, Namespace: check.Namespace}, updated); err != nil {
			return false, err
		}

		if updated.Status.Phase != lastPhase {
			fmt.Printf("Phase: %s\n", updated.Status.Phase)
			lastPhase = updated.Status.Phase
		}

		if updated.Status.Phase == validationv1alpha1.PhasePass || updated.Status.Phase == validationv1alpha1.PhaseFail {
			if updated.Status.Result != nil {
				data, _ := json.MarshalIndent(updated.Status.Result, "", "  ")
				fmt.Println(string(data))
			}
			return true, nil
		}

		if updated.Status.Phase == validationv1alpha1.PhaseError {
			return true, fmt.Errorf("check entered error phase")
		}

		return false, nil
	}); err != nil {
		return fmt.Errorf("waiting for check: %w", err)
	}

	_ = clientset
	return nil
}

func getConfig() (*rest.Config, error) {
	kubeconfig := os.Getenv("KUBECONFIG")
	if kubeconfig == "" {
		kubeconfig = clientcmd.RecommendedHomeFile
	}

	config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
	if err != nil {
		return rest.InClusterConfig()
	}
	return config, nil
}
