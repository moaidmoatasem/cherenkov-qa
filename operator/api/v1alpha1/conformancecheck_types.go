package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// ConformancePhase describes the lifecycle phase of a check.
type ConformancePhase string

const (
	PhasePending ConformancePhase = "Pending"
	PhaseRunning ConformancePhase = "Running"
	PhasePass    ConformancePhase = "Pass"
	PhaseFail    ConformancePhase = "Fail"
	PhaseError   ConformancePhase = "Error"
)

// Gate defines a specific conformance gate to validate.
type Gate struct {
	Name   string `json:"name"`
	Type   string `json:"type"`
	Assert string `json:"assert,omitempty"`
}

// TargetRef identifies the K8s resource to validate.
type TargetRef struct {
	APIVersion string `json:"apiVersion"`
	Kind       string `json:"kind"`
	Name       string `json:"name"`
	Namespace  string `json:"namespace"`
	Port       int32  `json:"port,omitempty"`
}

// CheckResult stores the last validation outcome.
type CheckResult struct {
	Passed      bool     `json:"passed"`
	Divergences []string `json:"divergences,omitempty"`
	Summary     string   `json:"summary,omitempty"`
}

// ViewportSize defines a browser viewport dimension.
type ViewportSize struct {
	Width  int `json:"width"`
	Height int `json:"height"`
}

// DeviceTarget defines a mobile or browser device target for validation.
// The DeviceID and Platform fields follow the cherenkov device API convention.
type DeviceTarget struct {
	// DeviceID is the unique identifier for the device (cherenkov device API).
	DeviceID string `json:"device_id"`
	// Platform is the device platform (ios, android, web).
	Platform string `json:"platform"`
	// DeviceClass is the optional device class (phone, tablet, desktop).
	DeviceClass string `json:"device_class,omitempty"`
	// Legacy fields kept for backward compatibility.
	OSVersion    string        `json:"osVersion,omitempty"`
	DeviceName   string        `json:"deviceName,omitempty"`
	Browser      string        `json:"browser,omitempty"`
	ViewportSize *ViewportSize `json:"viewportSize,omitempty"`
}

// VisualConfig defines visual regression testing configuration.
type VisualConfig struct {
	// VLMTier is the VLM tier to use for visual comparison (cherenkov VLM API).
	VLMTier             string            `json:"vlm_tier,omitempty"`
	// ExpectedScreenshots maps endpoint paths to expected screenshot paths.
	ExpectedScreenshots map[string]string `json:"expected_screenshots,omitempty"`
	// Legacy fields kept for backward compatibility.
	Enabled          bool    `json:"enabled,omitempty"`
	VLMProvider      string  `json:"vlmProvider,omitempty"`
	Threshold        float64 `json:"threshold,omitempty"`
	ScreenshotOnFail bool    `json:"screenshotOnFail,omitempty"`
	DiffMethod       string  `json:"diffMethod,omitempty"`
}

// TestResult stores a single test result from the last validation run.
type TestResult struct {
	Endpoint   string `json:"endpoint"`
	Method     string `json:"method"`
	Status     string `json:"status"`
	DeviceID   string `json:"device_id,omitempty"`
	Screenshot string `json:"screenshot,omitempty"`
}

// ConformanceCheckSpec defines the desired state.
type ConformanceCheckSpec struct {
	// SpecURL is the URL of the OpenAPI specification to validate against.
	SpecURL string `json:"specURL,omitempty"`
	// TargetURL is the URL of the target service to validate.
	TargetURL string `json:"targetURL,omitempty"`
	// TargetRef identifies the K8s resource to validate (legacy field).
	TargetRef TargetRef `json:"targetRef,omitempty"`
	// SpecRef is the name of a ConfigMap containing the spec (legacy field).
	SpecRef        string         `json:"specRef,omitempty"`
	Schedule       string         `json:"schedule,omitempty"`
	Gates          []Gate         `json:"gates,omitempty"`
	LLMConcurrency *int32         `json:"llmConcurrency,omitempty"`
	// DeviceTargets is the list of device targets for mobile/browser validation.
	DeviceTargets []DeviceTarget `json:"device_targets,omitempty"`
	// VisualConfig holds visual regression testing configuration.
	VisualConfig *VisualConfig `json:"visual_config,omitempty"`
}

// ConformanceCheckStatus defines the observed state.
type ConformanceCheckStatus struct {
	Phase      ConformancePhase   `json:"phase,omitempty"`
	Conditions []metav1.Condition `json:"conditions,omitempty"`
	LastRun    *metav1.Time       `json:"lastRun,omitempty"`
	Result     *CheckResult       `json:"result,omitempty"`
	// Results is the list of individual test results from the last run.
	Results []TestResult `json:"results,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Phase",type="string",JSONPath=".status.phase"
// +kubebuilder:printcolumn:name="LastRun",type="date",JSONPath=".status.lastRun"

type ConformanceCheck struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              ConformanceCheckSpec   `json:"spec,omitempty"`
	Status            ConformanceCheckStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

type ConformanceCheckList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []ConformanceCheck `json:"items"`
}

func init() {
	SchemeBuilder.Register(&ConformanceCheck{}, &ConformanceCheckList{})
}
