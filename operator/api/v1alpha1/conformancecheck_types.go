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

// ConformanceCheckSpec defines the desired state.
type ConformanceCheckSpec struct {
	TargetRef TargetRef `json:"targetRef"`
	SpecRef   string    `json:"specRef,omitempty"`
	Schedule  string    `json:"schedule,omitempty"`
	Gates     []Gate    `json:"gates,omitempty"`
	LLMConcurrency *int32 `json:"llmConcurrency,omitempty"`
}

// ConformanceCheckStatus defines the observed state.
type ConformanceCheckStatus struct {
	Phase      ConformancePhase    `json:"phase,omitempty"`
	Conditions []metav1.Condition  `json:"conditions,omitempty"`
	LastRun    *metav1.Time        `json:"lastRun,omitempty"`
	Result     *CheckResult        `json:"result,omitempty"`
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
