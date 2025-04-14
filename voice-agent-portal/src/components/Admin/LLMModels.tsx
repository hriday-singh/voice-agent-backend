import React, { useState, useEffect } from "react";
import {
  LLMProvider,
  LLMModel,
  fetchLLMProviders,
  fetchLLMModels,
  createLLMProvider,
  updateLLMProvider,
  deleteLLMProvider,
  createLLMModel,
  updateLLMModel,
  deleteLLMModel,
  LLMProviderCreate,
  LLMModelCreate,
} from "../../services/api";
import AnimatedLogo from "../Common/AnimatedLogo";
import "./Admin.css";

const LLMModels: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"providers" | "models">(
    "providers"
  );
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [models, setModels] = useState<LLMModel[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showAddProvider, setShowAddProvider] = useState<boolean>(false);
  const [showAddModel, setShowAddModel] = useState<boolean>(false);

  // Form states
  const [selectedProviderId, setSelectedProviderId] = useState<number | null>(
    null
  );
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const [newProvider, setNewProvider] = useState<LLMProviderCreate>({
    name: "",
    description: "",
    enabled: true,
  });
  const [newModel, setNewModel] = useState<LLMModelCreate>({
    provider_id: 0,
    name: "",
    display_name: "",
    default_temperature: 0.7,
  });

  useEffect(() => {
    loadProviders();
    loadModels();
  }, []);

  useEffect(() => {
    if (selectedProviderId) {
      loadModels(selectedProviderId);
      // Auto-update the new model form with the selected provider
      setNewModel((prev) => ({
        ...prev,
        provider_id: selectedProviderId,
      }));
    }
  }, [selectedProviderId]);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const providersData = await fetchLLMProviders();
      setProviders(providersData);

      // Select the first provider by default if none is selected
      if (providersData.length > 0 && !selectedProviderId) {
        setSelectedProviderId(providersData[0].id);
        setNewModel((prev) => ({ ...prev, provider_id: providersData[0].id }));
      }

      setError(null);
    } catch (err: any) {
      setError(`Error loading providers: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadModels = async (providerId?: number) => {
    try {
      setLoading(true);
      const modelsData = await fetchLLMModels(providerId);
      setModels(modelsData);
      setError(null);
    } catch (err: any) {
      setError(`Error loading models: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleProviderChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setNewProvider((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleModelChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setNewModel((prev) => ({
      ...prev,
      [name]:
        name === "provider_id" || name === "default_temperature"
          ? parseFloat(value)
          : value,
    }));

    // If provider_id is changed, also update the selected provider in the UI
    if (name === "provider_id") {
      setSelectedProviderId(parseInt(value, 10));
    }
  };

  const handleAddProvider = async () => {
    try {
      setLoading(true);
      const result = await createLLMProvider(newProvider);
      setSuccess(`Provider created successfully: ${result.message}`);
      setNewProvider({
        name: "",
        description: "",
        enabled: true,
      });
      setShowAddProvider(false);
      // Reload providers
      await loadProviders();
    } catch (err: any) {
      setError(`Error creating provider: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProvider = async (
    id: number,
    provider: Partial<LLMProviderCreate>
  ) => {
    try {
      setLoading(true);
      const result = await updateLLMProvider(id, provider);
      setSuccess(`Provider updated successfully: ${result.message}`);
      // Reload providers
      await loadProviders();
    } catch (err: any) {
      setError(`Error updating provider: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProvider = async (id: number) => {
    if (
      !window.confirm(
        "Are you sure you want to delete this provider? All associated models will also be deleted."
      )
    ) {
      return;
    }

    try {
      setLoading(true);
      const result = await deleteLLMProvider(id);
      setSuccess(`Provider deleted successfully: ${result.message}`);

      // Reset selected provider if the deleted one was selected
      if (selectedProviderId === id) {
        setSelectedProviderId(null);
      }

      // Reload providers
      await loadProviders();
    } catch (err: any) {
      setError(`Error deleting provider: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleAddModel = async () => {
    try {
      if (!newModel.provider_id) {
        setError("Please select a provider for the model");
        return;
      }

      setLoading(true);
      const result = await createLLMModel(newModel);
      setSuccess(`Model created successfully: ${result.message}`);
      setNewModel({
        provider_id: selectedProviderId || 0,
        name: "",
        display_name: "",
        default_temperature: 0.7,
      });
      setShowAddModel(false);
      // Reload models
      await loadModels(selectedProviderId || undefined);
    } catch (err: any) {
      setError(`Error creating model: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateModel = async (
    id: number,
    model: Partial<LLMModelCreate>
  ) => {
    try {
      setLoading(true);
      const result = await updateLLMModel(id, model);
      setSuccess(`Model updated successfully: ${result.message}`);
      // Reload models
      await loadModels(selectedProviderId || undefined);
    } catch (err: any) {
      setError(`Error updating model: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteModel = async (id: number) => {
    if (!window.confirm("Are you sure you want to delete this model?")) {
      return;
    }

    try {
      setLoading(true);
      const result = await deleteLLMModel(id);
      setSuccess(`Model deleted successfully: ${result.message}`);
      // Reload models
      await loadModels(selectedProviderId || undefined);
    } catch (err: any) {
      setError(`Error deleting model: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  if (loading && providers.length === 0 && models.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center">
          <AnimatedLogo
            gifSrc="/assets/caw-tech-logo.svg"
            fallbackSrc="/assets/caw-tech-logo.svg"
            alt="Loading..."
            height={64}
            width={64}
            className="rounded-lg shadow-md object-contain"
          />
          <p className="mt-4 text-[#6c6c6c]">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="bg-white shadow-md rounded-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-[#140d0c]">
            LLM Models & Providers
          </h2>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-md text-sm mb-4 flex justify-between items-center">
            <span>{error}</span>
            <button
              className="text-red-600 hover:text-red-800"
              onClick={clearMessages}
            >
              ×
            </button>
          </div>
        )}

        {success && (
          <div className="p-3 bg-green-50 border border-green-200 text-green-600 rounded-md text-sm mb-4 flex justify-between items-center">
            <span>{success}</span>
            <button
              className="text-green-600 hover:text-green-800"
              onClick={clearMessages}
            >
              ×
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b mb-6">
          <button
            className={`py-2 px-4 font-medium ${
              activeTab === "providers"
                ? "text-[#ffcc33] border-b-2 border-[#ffcc33]"
                : "text-gray-500 hover:text-[#140d0c]"
            }`}
            onClick={() => setActiveTab("providers")}
          >
            Providers
          </button>
          <button
            className={`py-2 px-4 font-medium ${
              activeTab === "models"
                ? "text-[#ffcc33] border-b-2 border-[#ffcc33]"
                : "text-gray-500 hover:text-[#140d0c]"
            }`}
            onClick={() => setActiveTab("models")}
          >
            Models
          </button>
        </div>

        {/* Providers Tab */}
        {activeTab === "providers" && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Providers</h3>
              <button
                onClick={() => setShowAddProvider(!showAddProvider)}
                className="px-3 py-1.5 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors flex items-center gap-1"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 4v16m8-8H4"
                  />
                </svg>
                {showAddProvider ? "Hide Form" : "Add Provider"}
              </button>
            </div>

            {/* Add Provider Form */}
            {showAddProvider && (
              <div className="bg-[#f2efe3] p-5 rounded-lg border border-[#e7e2d3] mb-6">
                <h4 className="font-medium text-[#140d0c] mb-3">
                  Add New Provider
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Provider Name
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={newProvider.name}
                      onChange={handleProviderChange}
                      placeholder="e.g. Anthropic, OpenAI, Google"
                      className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md focus:outline-none focus:ring-1 focus:ring-[#ffcc33]"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Description
                    </label>
                    <textarea
                      name="description"
                      value={newProvider.description}
                      onChange={handleProviderChange}
                      placeholder="Provider description"
                      rows={2}
                      className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md focus:outline-none focus:ring-1 focus:ring-[#ffcc33]"
                    />
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={handleAddProvider}
                      disabled={loading || !newProvider.name}
                      className="px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed flex-1"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 4v16m8-8H4"
                        />
                      </svg>
                      {loading ? "Adding..." : "Add Provider"}
                    </button>
                    <button
                      onClick={() => setShowAddProvider(false)}
                      className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Providers List */}
            <div className="space-y-4">
              {providers.length === 0 ? (
                <div className="bg-white rounded-lg shadow-sm p-4 text-center text-[#6c6c6c]">
                  No providers found. Add a new provider to get started.
                </div>
              ) : (
                providers.map((provider) => (
                  <div
                    key={provider.id}
                    className={`bg-white rounded-lg shadow-sm p-4 border border-[#e7e2d3] hover:shadow-md transition-all duration-200 cursor-pointer ${
                      selectedProviderId === provider.id
                        ? "border-[#ffcc33] border-2"
                        : ""
                    }`}
                    onClick={() => {
                      setSelectedProviderId(provider.id);
                      setActiveTab("models");
                    }}
                  >
                    <div className="flex justify-between items-center">
                      <h4 className="font-medium text-[#140d0c]">
                        {provider.name}
                      </h4>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteProvider(provider.id);
                          }}
                          className="p-1 text-red-500 hover:text-red-700 rounded-full hover:bg-red-50"
                        >
                          <svg
                            className="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                            />
                          </svg>
                        </button>
                      </div>
                    </div>
                    {provider.description && (
                      <p className="text-sm text-[#6c6c6c] mt-1">
                        {provider.description}
                      </p>
                    )}

                    <div className="mt-2 text-xs text-blue-500">
                      {
                        models.filter((m) => m.provider_id === provider.id)
                          .length
                      }{" "}
                      models associated
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Models Tab */}
        {activeTab === "models" && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-medium">Models</h3>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-[#6c6c6c]">Filter by:</span>
                  <select
                    value={selectedProviderId || ""}
                    onChange={(e) =>
                      setSelectedProviderId(
                        e.target.value ? parseInt(e.target.value, 10) : null
                      )
                    }
                    className="text-sm px-2 py-1 border border-[#e7e2d3] rounded-md focus:outline-none focus:ring-1 focus:ring-[#ffcc33]"
                  >
                    <option value="">All Providers</option>
                    {providers.map((provider) => (
                      <option key={provider.id} value={provider.id}>
                        {provider.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <button
                onClick={() => setShowAddModel(!showAddModel)}
                className="px-3 py-1.5 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors flex items-center gap-1"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 4v16m8-8H4"
                  />
                </svg>
                {showAddModel ? "Hide Form" : "Add Model"}
              </button>
            </div>

            {/* Add Model Form */}
            {showAddModel && (
              <div className="bg-[#f2efe3] p-5 rounded-lg border border-[#e7e2d3] mb-6">
                <h4 className="font-medium text-[#140d0c] mb-3">
                  Add New Model
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Provider
                    </label>
                    <select
                      name="provider_id"
                      value={newModel.provider_id || ""}
                      onChange={handleModelChange}
                      className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md focus:outline-none focus:ring-1 focus:ring-[#ffcc33]"
                    >
                      <option value="">-- Select Provider --</option>
                      {providers.map((provider) => (
                        <option key={provider.id} value={provider.id}>
                          {provider.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Model ID/Name
                      </label>
                      <input
                        type="text"
                        name="name"
                        value={newModel.name}
                        onChange={handleModelChange}
                        placeholder="e.g. claude-3-5-sonnet-20240620"
                        className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md focus:outline-none focus:ring-1 focus:ring-[#ffcc33]"
                      />
                      <p className="text-xs text-[#6c6c6c] mt-1">
                        The exact model identifier used by the provider
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Display Name
                      </label>
                      <input
                        type="text"
                        name="display_name"
                        value={newModel.display_name}
                        onChange={handleModelChange}
                        placeholder="e.g. Claude 3.5 Sonnet"
                        className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md focus:outline-none focus:ring-1 focus:ring-[#ffcc33]"
                      />
                      <p className="text-xs text-[#6c6c6c] mt-1">
                        Human-friendly name shown in UI
                      </p>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Default Temperature: {newModel.default_temperature}
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      name="default_temperature"
                      value={newModel.default_temperature}
                      onChange={handleModelChange}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-[#6c6c6c]">
                      <span>0.0 (Precise)</span>
                      <span>1.0 (Creative)</span>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={handleAddModel}
                      disabled={
                        loading ||
                        !newModel.name ||
                        !newModel.display_name ||
                        !newModel.provider_id
                      }
                      className="px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed flex-1"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 4v16m8-8H4"
                        />
                      </svg>
                      {loading ? "Adding..." : "Add Model"}
                    </button>
                    <button
                      onClick={() => setShowAddModel(false)}
                      className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Models List */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {models.length === 0 ? (
                <div className="col-span-full bg-white rounded-lg shadow-sm p-4 text-center text-[#6c6c6c]">
                  No models found.{" "}
                  {providers.length > 0
                    ? "Add a new model to get started."
                    : "Add a provider first."}
                </div>
              ) : (
                models.map((model) => (
                  <div
                    key={model.id}
                    className="bg-white rounded-lg shadow-sm p-4 border border-[#e7e2d3] hover:shadow-md transition-all duration-200"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-medium text-[#140d0c]">
                          {model.display_name}
                        </h4>
                        <p className="text-sm text-[#6c6c6c] mt-1">
                          ID: {model.name}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-800 rounded-full">
                            {model.provider
                              ? model.provider.name
                              : providers.find(
                                  (p) => p.id === model.provider_id
                                )?.name || "Unknown Provider"}
                          </span>
                          <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-800 rounded-full">
                            Temp: {model.default_temperature}
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteModel(model.id)}
                        className="p-1 text-red-500 hover:text-red-700 rounded-full hover:bg-red-50"
                      >
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LLMModels;
