define([
    'dojo/text!./templates/MapLayersPopover.html',

    'dojo/_base/declare',
    'dojo/dom-construct',

    'dijit/_WidgetBase',
    'dijit/_TemplatedMixin',
    'dijit/_WidgetsInTemplateMixin',

    'app/map/ReferenceLayerToggle',
    'app/map/ScaleDependentReferenceLayerToggle',
    'app/config',
    'app/map/MapController',
    'app/map/BaseMapSelector',
    'app/_PopoverMixin'
], function(
    template,

    declare,
    domConstruct,

    _WidgetBase,
    _TemplatedMixin,
    _WidgetsInTemplateMixin,

    ReferenceLayerToggle,
    ScaleDependentReferenceLayerToggle,
    config,
    MapController,
    BaseMapSelector,
    _PopoverMixin
) {
    return declare([_WidgetBase, _TemplatedMixin, _WidgetsInTemplateMixin, _PopoverMixin], {
        // description:
        //      Popover that is toggled by the "Map Layers" map button. 
        //      Contains controls to allow the user to toggle reference and base map layers.

        templateString: template,
        baseClass: 'map-layers-popover',
        widgetsInTemplate: true,


        // Properties to be sent into constructor

        postCreate: function() {
            // summary:
            //    Overrides method of same name in dijit._Widget.
            // tags:
            //    private
            console.log('app/map/MapLayersPopover::postCreate', arguments);

            this.own(
                // needs to be loaded first before other layers are added to the map
                new BaseMapSelector({
                    map: MapController.map
                }, domConstruct.create('div', {}, this.domNode)),
                new ReferenceLayerToggle({
                    layerName: 'Environmental Investigation of UST Facilities',
                    mapServiceUrl: config.urls.DEQEnviro,
                    layerIndex: 4,
                    showLegend: true,
                    legendHeader: 'TankRiskAverageTest'
                }, domConstruct.create('div', {}, this.domNode, 'first')),
                new ScaleDependentReferenceLayerToggle({
                    layerName: 'Environmental Risk Water Points',
                    mapServiceUrl: config.urls.DEQEnviro,
                    layerIndex: 5,
                    layerProps: {opacity: 0.4},
                    showLegend: true,
                    minScaleLevel: config.RiskLayersMinScaleLevel
                }, domConstruct.create('div', {}, this.domNode, 'first')),
                new ScaleDependentReferenceLayerToggle({
                    layerName: 'Environmental Risk Streams',
                    mapServiceUrl: config.urls.DEQEnviro,
                    layerIndex: 6,
                    layerProps: {opacity: 0.4},
                    showLegend: true,
                    minScaleLevel: config.RiskLayersMinScaleLevel
                }, domConstruct.create('div', {}, this.domNode, 'first')),
                new ScaleDependentReferenceLayerToggle({
                    layerName: 'Environmental Risk Lakes',
                    mapServiceUrl: config.urls.DEQEnviro,
                    layerIndex: 7,
                    layerProps: {opacity: 0.4},
                    showLegend: true,
                    minScaleLevel: config.RiskLayersMinScaleLevel
                }, domConstruct.create('div', {}, this.domNode, 'first')),
                new ReferenceLayerToggle({
                    layerName: 'Indian Country and Tribal',
                    mapServiceUrl: config.urls.DEQEnviro,
                    layerIndex: 3,
                    layerProps: {opacity: 0.7},
                    showLegend: true
                }, domConstruct.create('div', {}, this.domNode, 'first')),
                new ReferenceLayerToggle({
                    layerName: 'Land Ownership',
                    mapServiceUrl: config.urls.DEQEnviro,
                    layerIndex: 0,
                    layerProps: {opacity: 0.7},
                    showLegend: true
                }, domConstruct.create('div', {}, this.domNode, 'first')),
                new ReferenceLayerToggle({
                    layerName: 'Hydrologic Units',
                    mapServiceUrl: config.urls.DEQEnviro,
                    layerIndex: 2,
                    layerProps: {opacity: 0.7}
                }, domConstruct.create('div', {}, this.domNode, 'first')),
                new ScaleDependentReferenceLayerToggle({
                    layerName: 'Township/Range/Section',
                    mapServiceUrl: config.urls.UtahPLSS,
                    tiledService: true,
                    minScaleLevel: config.TRSMinScaleLevel
                }, domConstruct.create('div', {}, this.domNode, 'first')),
                new ReferenceLayerToggle({
                    layerName: 'Environmental Covenants',
                    mapServiceUrl: config.urls.DEQEnviro,
                    layerIndex: 1,
                    layerProps: {opacity: 0.7},
                    showLegend: true,
                    legendHeader: 'DIVISION, BRANCH, PROGRAM'
                }, domConstruct.create('div', {}, this.domNode, 'first'))
            );

            this.inherited(arguments);
        }
    });
});
